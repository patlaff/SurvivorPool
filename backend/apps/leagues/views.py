from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers as rest_framework_serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.castaways.models import Castaway, Episode
from apps.castaways.serializers import CastawaySerializer
from apps.scoring.models import PlayerEpisodeScore
from .models import League, Membership, Perk, Roster, RosterSlot
from .permissions import IsLeagueMember, IsLeagueOwner
from .serializers import (
    EpisodeScoreSerializer,
    LeagueDetailSerializer,
    LeagueSerializer,
    RosterSerializer,
)
from .utils import is_draft_open


def _get_league_for_member(slug, user):
    league = get_object_or_404(League, slug=slug)
    get_object_or_404(Membership, league=league, user=user)
    return league


# ── League CRUD ───────────────────────────────────────────────────────────────

class LeagueListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LeagueSerializer

    def get_queryset(self):
        return League.objects.filter(memberships__user=self.request.user).select_related('season', 'owner')

    def perform_create(self, serializer):
        from apps.castaways.models import Season
        from rest_framework.exceptions import ValidationError
        season = Season.objects.filter(is_active=True, version='US').first()
        if season is None:
            raise ValidationError(
                'No active US season found. Run "sync_season <number>" to load season data first.'
            )
        with transaction.atomic():
            league = serializer.save(owner=self.request.user, season=season)
            Membership.objects.create(league=league, user=self.request.user)


class LeagueDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    queryset = League.objects.select_related('season', 'owner').prefetch_related('memberships__user')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return LeagueDetailSerializer
        return LeagueSerializer

    def get_object(self):
        obj = super().get_object()
        get_object_or_404(Membership, league=obj, user=self.request.user)
        return obj

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.owner != request.user:
            return Response({'detail': 'Only the league owner can edit.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


class LeagueJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        league = get_object_or_404(League, slug=slug)
        invite_code = request.data.get('invite_code', '')
        if league.invite_code != invite_code:
            return Response({'detail': 'Invalid invite code.'}, status=status.HTTP_400_BAD_REQUEST)
        _, created = Membership.objects.get_or_create(league=league, user=request.user)
        if not created:
            return Response({'detail': 'Already a member.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Joined successfully.'})


class LeagueJoinByCodeView(APIView):
    """Join a league using only an invite code — no slug required."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        invite_code = request.data.get('invite_code', '').strip()
        if not invite_code:
            return Response({'detail': 'Provide an invite_code.'}, status=status.HTTP_400_BAD_REQUEST)
        league = get_object_or_404(League, invite_code=invite_code)
        _, created = Membership.objects.get_or_create(league=league, user=request.user)
        if not created:
            return Response({'detail': 'Already a member.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Joined successfully.', 'slug': league.slug})


# ── Available castaways ───────────────────────────────────────────────────────

class AvailableCastawaysView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        league = _get_league_for_member(slug, request.user)
        picked_ids = RosterSlot.objects.filter(
            roster__league=league
        ).values_list('castaway_id', flat=True)
        available = Castaway.objects.filter(
            season=league.season
        ).exclude(id__in=picked_ids)
        return Response(CastawaySerializer(available, many=True).data)


# ── Draft ─────────────────────────────────────────────────────────────────────

class DraftView(APIView):
    permission_classes = [IsAuthenticated]

    def _league(self, slug, user):
        return _get_league_for_member(slug, user)

    def get(self, request, slug):
        league = self._league(slug, request.user)
        roster = Roster.objects.filter(league=league, user=request.user).prefetch_related('slots__castaway').first()
        # Effective lock date: league override takes precedence over season default.
        lock_date = league.draft_close_at if league.draft_close_at is not None else league.season.draft_lock_date
        picks = []
        if roster:
            picks = [slot.castaway.castaway_id for slot in roster.slots.all()]
        return Response({
            'draft_open': is_draft_open(league),
            'lock_date': lock_date,
            'picks': picks,
        })

    def put(self, request, slug):
        league = self._league(slug, request.user)
        if not is_draft_open(league):
            return Response(
                {'detail': 'Draft is closed.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        castaway_ids = request.data.get('castaway_ids', [])
        if len(castaway_ids) != 5:
            return Response({'detail': 'You must pick exactly 5 castaways.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(set(castaway_ids)) != 5:
            return Response({'detail': 'Duplicate castaways in selection.'}, status=status.HTTP_400_BAD_REQUEST)

        castaways = Castaway.objects.filter(castaway_id__in=castaway_ids, season=league.season)
        if castaways.count() != 5:
            return Response({'detail': 'One or more castaways not found in this season.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check each castaway not already picked by another roster in this league
        already_taken = RosterSlot.objects.filter(
            roster__league=league,
            castaway__castaway_id__in=castaway_ids,
        ).exclude(roster__user=request.user)
        if already_taken.exists():
            taken_names = list(already_taken.values_list('castaway__name', flat=True))
            return Response(
                {'detail': f'Already drafted by another player: {", ".join(taken_names)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            roster, _ = Roster.objects.get_or_create(league=league, user=request.user)
            roster.slots.all().delete()
            castaway_map = {c.castaway_id: c for c in castaways}
            for i, cid in enumerate(castaway_ids, start=1):
                RosterSlot.objects.create(roster=roster, castaway=castaway_map[cid], slot_number=i)
            # Create perks if not already present
            for perk_type in (Perk.SWAP, Perk.BOOST):
                Perk.objects.get_or_create(roster=roster, perk_type=perk_type)

        return Response({'detail': 'Draft saved.'})


# ── Draft Window Control ──────────────────────────────────────────────────────

class _DraftWindowSerializer(rest_framework_serializers.Serializer):
    """Internal serializer for parsing DraftWindowView input."""
    draft_close_at = rest_framework_serializers.DateTimeField(required=False, allow_null=True)
    draft_force_open = rest_framework_serializers.BooleanField(required=False)


class DraftWindowView(APIView):
    """
    PATCH /leagues/<slug>/draft-window/

    League-owner-only endpoint to control the draft window.
    Accepts any combination of draft_close_at (ISO 8601 datetime or null)
    and draft_force_open (bool).
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, slug):
        league = get_object_or_404(League, slug=slug)
        if league.owner != request.user:
            return Response(
                {'detail': 'Only the league owner can update the draft window.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = _DraftWindowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        update_fields = []
        if 'draft_close_at' in validated:
            league.draft_close_at = validated['draft_close_at']
            update_fields.append('draft_close_at')
        if 'draft_force_open' in validated:
            league.draft_force_open = validated['draft_force_open']
            update_fields.append('draft_force_open')

        if not update_fields:
            return Response({'detail': 'No fields provided.'}, status=status.HTTP_400_BAD_REQUEST)

        league.save(update_fields=update_fields)
        return Response(LeagueDetailSerializer(league).data)


# ── Roster & Perks ────────────────────────────────────────────────────────────

class RosterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug, user_id=None):
        league = _get_league_for_member(slug, request.user)
        if user_id:
            roster = get_object_or_404(Roster, league=league, user_id=user_id)
        else:
            roster = get_object_or_404(Roster, league=league, user=request.user)
        return Response(RosterSerializer(roster).data)


class SwapPerkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        league = _get_league_for_member(slug, request.user)
        roster = get_object_or_404(Roster, league=league, user=request.user)

        # Swap requires the draft to be closed (picks are locked)
        if is_draft_open(league):
            return Response(
                {'detail': 'Swaps are only available after the draft closes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Swap window closes when the merge episode airs
        merge_ep = Episode.objects.filter(
            season=league.season, is_merge=True
        ).order_by('episode_number').first()
        if merge_ep and merge_ep.air_date <= timezone.now().date():
            return Response(
                {'detail': 'Swap perk has expired — the tribes have merged.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        perk = get_object_or_404(Perk, roster=roster, perk_type=Perk.SWAP)
        if perk.used:
            return Response({'detail': 'Swap perk already used.'}, status=status.HTTP_400_BAD_REQUEST)

        out_id = request.data.get('out_id')
        in_id = request.data.get('in_id')
        if not out_id or not in_id:
            return Response({'detail': 'Provide out_id and in_id.'}, status=status.HTTP_400_BAD_REQUEST)

        slot = get_object_or_404(RosterSlot, roster=roster, castaway__castaway_id=out_id)
        new_castaway = get_object_or_404(Castaway, castaway_id=in_id, season=league.season)

        taken = RosterSlot.objects.filter(roster__league=league, castaway=new_castaway).exclude(roster=roster)
        if taken.exists():
            return Response({'detail': 'That castaway is already on another roster.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            perk.swapped_out_castaway = slot.castaway
            perk.swapped_in_castaway = new_castaway
            perk.used = True
            perk.used_at = timezone.now()
            perk.save()
            slot.castaway = new_castaway
            slot.save()

        return Response({'detail': 'Swap complete.'})


class BoostPerkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        league = _get_league_for_member(slug, request.user)
        roster = get_object_or_404(Roster, league=league, user=request.user)
        perk = get_object_or_404(Perk, roster=roster, perk_type=Perk.BOOST)

        if perk.used:
            return Response({'detail': 'Boost perk already used.'}, status=status.HTTP_400_BAD_REQUEST)

        episode_number = request.data.get('episode_number')
        if not episode_number:
            return Response({'detail': 'Provide episode_number.'}, status=status.HTTP_400_BAD_REQUEST)

        episode = get_object_or_404(Episode, season=league.season, episode_number=episode_number)
        if episode.scored_at is not None:
            return Response({'detail': 'That episode has already been scored.'}, status=status.HTTP_400_BAD_REQUEST)
        if episode.air_date <= timezone.now().date():
            return Response({'detail': 'That episode has already aired.'}, status=status.HTTP_400_BAD_REQUEST)
        if episode.is_finale:
            return Response({'detail': 'Boost cannot be applied to the finale.'}, status=status.HTTP_400_BAD_REQUEST)

        perk.boost_target_episode = episode_number
        perk.used = True
        perk.used_at = timezone.now()
        perk.save()
        return Response({'detail': f'Boost applied to episode {episode_number}.'})


# ── Scores & Leaderboard ──────────────────────────────────────────────────────

class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        league = _get_league_for_member(slug, request.user)
        rosters = Roster.objects.filter(league=league).prefetch_related(
            'user', 'episode_scores__episode'
        )
        entries = []
        for roster in rosters:
            scores = list(roster.episode_scores.order_by('episode__episode_number'))
            total = sum(s.final_points for s in scores)
            entries.append({
                'roster': roster,
                'user': roster.user,
                'total_points': total,
                'episodes': scores,
            })
        entries.sort(key=lambda e: e['total_points'], reverse=True)

        last_scored = (
            Episode.objects.filter(season=league.season, scored_at__isnull=False)
            .order_by('-scored_at')
            .values_list('scored_at', flat=True)
            .first()
        )

        results = []
        for rank, entry in enumerate(entries, start=1):
            results.append({
                'rank': rank,
                'user': {
                    'id': entry['user'].id,
                    'email': entry['user'].email,
                    'display_name': entry['user'].display_name,
                    'avatar_url': entry['user'].avatar_url,
                },
                'total_points': entry['total_points'],
                'episodes': EpisodeScoreSerializer(entry['episodes'], many=True).data,
            })
        return Response({'entries': results, 'last_scored_at': last_scored})


class MyScoresView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EpisodeScoreSerializer

    def get_queryset(self):
        league = _get_league_for_member(self.kwargs['slug'], self.request.user)
        roster = get_object_or_404(Roster, league=league, user=self.request.user)
        return PlayerEpisodeScore.objects.filter(roster=roster).select_related('episode').order_by('episode__episode_number')


class EpisodeScoresView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug, episode_number):
        league = _get_league_for_member(slug, request.user)
        episode = get_object_or_404(Episode, season=league.season, episode_number=episode_number)
        scores = PlayerEpisodeScore.objects.filter(
            episode=episode, roster__league=league
        ).select_related('roster__user')
        result = []
        for s in scores:
            result.append({
                'user': {
                    'id': s.roster.user.id,
                    'display_name': s.roster.user.display_name,
                    'avatar_url': s.roster.user.avatar_url,
                },
                'raw_points': s.raw_points,
                'multiplier': str(s.multiplier),
                'final_points': s.final_points,
            })
        return Response(result)
