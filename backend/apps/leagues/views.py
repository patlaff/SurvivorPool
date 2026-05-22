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
from .models import DraftSave, League, Membership, Perk, Roster, RosterSlot
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
        # Picks are non-exclusive — all castaways in the season are always available.
        available = Castaway.objects.filter(season=league.season)
        return Response(CastawaySerializer(available, many=True).data)


# ── Draft ─────────────────────────────────────────────────────────────────────

class DraftView(APIView):
    permission_classes = [IsAuthenticated]

    def _league(self, slug, user):
        return _get_league_for_member(slug, user)

    def get(self, request, slug):
        league = self._league(slug, request.user)
        roster = Roster.objects.filter(league=league, user=request.user).prefetch_related('slots__castaway').first()
        # Effective lock date is only meaningful when there's an actual deadline.
        # When draft_force_open or is_test is set, return null so the frontend
        # countdown doesn't show a misleading "Draft closed" against the past
        # season lock date.
        if league.is_test or league.draft_force_open:
            lock_date = None
        elif league.draft_close_at is not None:
            lock_date = league.draft_close_at
        else:
            lock_date = league.season.draft_lock_date
        picks = []
        if roster:
            picks = [slot.castaway.castaway_id for slot in roster.slots.all()]
        return Response({
            'draft_open': is_draft_open(league),
            'lock_date': lock_date,
            'picks': picks,
        })

    def put(self, request, slug):
        from decimal import Decimal
        from apps.castaways.models import Episode as EpisodeModel
        from apps.scoring.models import PlayerEpisodeScore, ScoringEvent

        league = self._league(slug, request.user)
        if not league.is_test and not is_draft_open(league):
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

        if not league.is_test and not league.draft_force_open:
            # Block drafting eliminated castaways during a normal draft window.
            # Bypassed for force-open (owner reopened mid-season) and test leagues.
            eliminated = [c.name for c in castaways if c.is_eliminated]
            if eliminated:
                return Response(
                    {'detail': f'Cannot draft eliminated castaways: {", ".join(eliminated)}'},
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

        # Backfill PlayerEpisodeScore for any already-scored episodes so total_points
        # reflects the new picks immediately (handles the case where scoring ran before
        # picks were saved).
        # castaway_ids are string IDs (e.g. "US0477"); ScoringEvent.castaway_id is the
        # integer FK PK, so we must resolve to PKs first.
        castaway_pks = list(castaways.values_list('pk', flat=True))
        scored_episodes = EpisodeModel.objects.filter(
            season=league.season,
            scored_at__isnull=False,
        )
        roster.refresh_from_db()  # ensure perks are visible
        for episode in scored_episodes:
            raw = sum(
                ScoringEvent.objects.filter(
                    castaway_id__in=castaway_pks,
                    episode=episode,
                ).values_list('points', flat=True)
            )
            multiplier = Decimal('1.0')
            try:
                roster.perks.get(
                    perk_type=Perk.BOOST,
                    used=True,
                    boost_target_episode=episode.episode_number,
                )
                multiplier = Decimal('2.0')
            except Perk.DoesNotExist:
                pass
            PlayerEpisodeScore.objects.update_or_create(
                roster=roster,
                episode=episode,
                defaults={
                    'raw_points': raw,
                    'multiplier': multiplier,
                    'final_points': int(raw * multiplier),
                },
            )

        DraftSave.objects.create(
            roster=roster,
            castaway_names=[castaway_map[cid].name for cid in castaway_ids],
        )

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


# ── League Activity Log ───────────────────────────────────────────────────────

class LeagueActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        league = get_object_or_404(League, slug=slug)
        if league.owner != request.user:
            return Response(
                {'detail': 'Only the league owner can view the activity log.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        events = []

        # Draft saves — hidden while the draft window is open to preserve pick privacy.
        if not is_draft_open(league):
            for ds in (
                DraftSave.objects
                .filter(roster__league=league)
                .select_related('roster__user')
                .order_by('saved_at')
            ):
                events.append({
                    'type': 'draft_saved',
                    'timestamp': ds.saved_at,
                    'user': {
                        'id': ds.roster.user.id,
                        'display_name': ds.roster.user.display_name,
                        'avatar_url': ds.roster.user.avatar_url,
                    },
                    'detail': {'castaways': ds.castaway_names},
                })

        # Swap perks
        for perk in (
            Perk.objects
            .filter(roster__league=league, perk_type=Perk.SWAP, used=True)
            .select_related('roster__user', 'swapped_out_castaway', 'swapped_in_castaway')
            .order_by('used_at')
        ):
            events.append({
                'type': 'swap_used',
                'timestamp': perk.used_at,
                'user': {
                    'id': perk.roster.user.id,
                    'display_name': perk.roster.user.display_name,
                    'avatar_url': perk.roster.user.avatar_url,
                },
                'detail': {
                    'dropped': perk.swapped_out_castaway.name if perk.swapped_out_castaway else None,
                    'added': perk.swapped_in_castaway.name if perk.swapped_in_castaway else None,
                },
            })

        # Boost perks
        for perk in (
            Perk.objects
            .filter(roster__league=league, perk_type=Perk.BOOST, used=True)
            .select_related('roster__user')
            .order_by('used_at')
        ):
            events.append({
                'type': 'boost_used',
                'timestamp': perk.used_at,
                'user': {
                    'id': perk.roster.user.id,
                    'display_name': perk.roster.user.display_name,
                    'avatar_url': perk.roster.user.avatar_url,
                },
                'detail': {'episode': perk.boost_target_episode},
            })

        events.sort(key=lambda e: e['timestamp'] or '', reverse=True)
        return Response(events)


# ── Roster & Perks ────────────────────────────────────────────────────────────

class RosterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug, user_id=None):
        league = _get_league_for_member(slug, request.user)
        if user_id:
            # Viewing another member's roster is only allowed once the draft is closed.
            if is_draft_open(league):
                return Response(
                    {'detail': "Other players' rosters are hidden until the draft closes."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            roster = get_object_or_404(Roster, league=league, user_id=user_id)
        else:
            roster = get_object_or_404(Roster, league=league, user=request.user)
        return Response(RosterSerializer(roster).data)


class SwapPerkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        league = _get_league_for_member(slug, request.user)
        roster = get_object_or_404(Roster, league=league, user=request.user)

        if not league.is_test:
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
        if not league.is_test:
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
        draft_open = is_draft_open(league)
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
            is_own = entry['user'].id == request.user.id
            roster_hidden = draft_open and not is_own
            results.append({
                'rank': rank,
                'user': {
                    'id': entry['user'].id,
                    'email': entry['user'].email,
                    'display_name': entry['user'].display_name,
                    'avatar_url': entry['user'].avatar_url,
                },
                'total_points': entry['total_points'],
                # Hide per-episode breakdown for other players while the draft is open
                # so nobody can infer picks from score patterns.
                'episodes': EpisodeScoreSerializer(entry['episodes'], many=True).data if not roster_hidden else [],
                'roster_hidden': roster_hidden,
            })
        return Response({'entries': results, 'last_scored_at': last_scored, 'draft_open': draft_open})


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
