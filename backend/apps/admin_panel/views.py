import json
import logging
import os
import tempfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.castaways.models import Season, Castaway
from apps.leagues.models import League, Membership, Roster
from apps.leagues.serializers import LeagueDetailSerializer
from apps.leagues.utils import is_draft_open
from apps.scoring.models import PlayerEpisodeScore, ScoringEvent
from .permissions import IsSuperAdmin


def _load_config() -> dict:
    path = Path(getattr(settings, 'SCORING_CONFIG_PATH', settings.BASE_DIR.parent / 'scoring_config.json'))
    with open(path) as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    path = Path(getattr(settings, 'SCORING_CONFIG_PATH', settings.BASE_DIR.parent / 'scoring_config.json'))
    # Write directly — scoring_config.json is a bind-mount so cross-fs rename is not possible.
    path.write_text(json.dumps(config, indent=2))


# ── Admin: All Leagues ────────────────────────────────────────────────────────

class AdminLeaguesView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        leagues = (
            League.objects
            .select_related('season', 'owner')
            .prefetch_related('memberships')
            .order_by('-created_at')
        )
        data = []
        for league in leagues:
            data.append({
                'id': league.id,
                'name': league.name,
                'slug': league.slug,
                'owner': {
                    'id': league.owner.id,
                    'display_name': league.owner.display_name,
                    'email': league.owner.email,
                },
                'member_count': league.memberships.count(),
                'season_number': league.season.season_number,
                'is_test': league.is_test,
                'is_archived': league.is_archived,
                'invite_code': league.invite_code,
                'draft_open': is_draft_open(league),
                'created_at': league.created_at,
            })
        return Response(data)

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'detail': 'Provide a league name.'}, status=status.HTTP_400_BAD_REQUEST)

        season = Season.objects.filter(is_active=True, version='US').first()
        if season is None:
            return Response({'detail': 'No active US season found.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            league = League.objects.create(
                name=name,
                season=season,
                owner=request.user,
                is_test=True,
            )
            Membership.objects.create(league=league, user=request.user)

        return Response(LeagueDetailSerializer(league).data, status=status.HTTP_201_CREATED)


# ── Admin: Season Scoring Summary ─────────────────────────────────────────────

class AdminScoringSummaryView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, season_number):
        events = (
            ScoringEvent.objects
            .filter(episode__season__season_number=season_number, episode__season__version='US')
            .select_related('castaway', 'episode')
            .order_by('episode__episode_number', 'castaway__name')
        )

        # Group by episode
        episodes_map = defaultdict(list)
        for ev in events:
            episodes_map[ev.episode].append(ev)

        scored_episodes = []
        for episode, ep_events in sorted(episodes_map.items(), key=lambda x: x[0].episode_number):
            scored_episodes.append({
                'episode_number': episode.episode_number,
                'air_date': episode.air_date,
                'scored_at': episode.scored_at,
                'events': [
                    {
                        'castaway_id': ev.castaway.castaway_id,
                        'castaway_name': ev.castaway.display_name,
                        'event_name': ev.event_name,
                        'points': ev.points,
                    }
                    for ev in ep_events
                ],
                'episode_total': sum(ev.points for ev in ep_events),
            })

        # Per-castaway totals
        castaway_totals_map = defaultdict(lambda: {'points': 0, 'castaway': None})
        for ev in events:
            key = ev.castaway.castaway_id
            castaway_totals_map[key]['points'] += ev.points
            castaway_totals_map[key]['castaway'] = ev.castaway

        castaway_totals = sorted(
            [
                {
                    'castaway_id': cid,
                    'name': v['castaway'].display_name,
                    'total_points': v['points'],
                    'is_eliminated': v['castaway'].is_eliminated,
                }
                for cid, v in castaway_totals_map.items()
            ],
            key=lambda x: x['total_points'],
            reverse=True,
        )

        return Response({
            'season_number': season_number,
            'scored_episodes': scored_episodes,
            'castaway_totals': castaway_totals,
        })


# ── Admin: Scoring Config ─────────────────────────────────────────────────────

class AdminScoringConfigView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        try:
            config = _load_config()
        except FileNotFoundError:
            return Response({'detail': 'scoring_config.json not found.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'config': config})

    def put(self, request):
        config = request.data.get('config')
        if not isinstance(config, dict):
            return Response({'detail': 'Provide a "config" object.'}, status=status.HTTP_400_BAD_REQUEST)
        for key, val in config.items():
            if not isinstance(val, int):
                return Response(
                    {'detail': f'Value for "{key}" must be an integer, got {val!r}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        _save_config(config)
        return Response({'config': config})


# ── Admin: Rescore Season ─────────────────────────────────────────────────────

class AdminScoringRescore(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, season_number):
        try:
            config = _load_config()
        except FileNotFoundError:
            return Response({'detail': 'scoring_config.json not found.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update ScoringEvent.points for all events in this season
        events = ScoringEvent.objects.filter(
            episode__season__season_number=season_number,
            episode__season__version='US',
        ).select_related('episode')

        updated_events = 0
        episode_ids_rescored = set()
        with transaction.atomic():
            for ev in events:
                new_points = config.get(ev.event_name)
                if new_points is None:
                    continue
                if ev.points != new_points:
                    ev.points = new_points
                    ev.save(update_fields=['points'])
                episode_ids_rescored.add(ev.episode_id)
                updated_events += 1

            # Upsert PlayerEpisodeScore for all rosters × all scored episodes in this season
            from apps.castaways.models import Episode
            from apps.leagues.models import Perk
            scored_episodes = list(
                Episode.objects.filter(
                    season__season_number=season_number,
                    season__version='US',
                    scored_at__isnull=False,
                )
            )

            rosters = Roster.objects.filter(
                league__season__season_number=season_number,
                league__season__version='US',
            ).prefetch_related('slots__castaway', 'perks')

            rosters_updated = 0
            for roster in rosters:
                castaway_ids = list(roster.slots.values_list('castaway_id', flat=True))
                for episode in scored_episodes:
                    raw = sum(
                        ScoringEvent.objects.filter(
                            castaway_id__in=castaway_ids,
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
                    except Exception:
                        pass
                    final = int(raw * multiplier)
                    _, created = PlayerEpisodeScore.objects.update_or_create(
                        roster=roster,
                        episode=episode,
                        defaults={
                            'raw_points': raw,
                            'multiplier': multiplier,
                            'final_points': final,
                        },
                    )
                    rosters_updated += 1

        return Response({
            'episodes_rescored': len(episode_ids_rescored),
            'rosters_updated': rosters_updated,
        })


# ── Admin: Archive Season ─────────────────────────────────────────────────────

class AdminArchiveSeasonView(APIView):
    """
    POST /api/v1/admin/archive-season/<season_number>/

    Archives all leagues for the given season and marks the season as no longer
    accepting new leagues.  This is the "State 1 → dormant" transition.
    The season remains is_active=True so the daily sync continues; use
    AdminProgressSeasonView to fully transition to the next season.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, season_number):
        from django.utils import timezone
        season = get_object_or_404(Season, season_number=season_number, version='US')
        leagues = League.objects.filter(season=season)
        count = leagues.count()
        leagues.update(
            is_archived=True,
            draft_force_open=False,
            draft_close_at=timezone.now(),
        )
        season.allows_new_leagues = False
        season.save(update_fields=['allows_new_leagues'])
        return Response({'detail': f'Archived {count} league(s) for Season {season_number}.'})


# ── Admin: Unarchive Season (testing only) ────────────────────────────────────

class AdminUnarchiveSeasonView(APIView):
    """
    POST /api/v1/admin/unarchive-season/<season_number>/

    Reverses an archive action for testing purposes:
      - Sets is_archived=False on all leagues for the season
      - Sets allows_new_leagues=True on the season
      - Clears next_detected_at and next_complete_notified_at

    Does NOT restore draft windows — use draft_force_open on individual leagues
    if you need drafts to be open again after unarchiving.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, season_number):
        season = get_object_or_404(Season, season_number=season_number, version='US')
        leagues = League.objects.filter(season=season)
        count = leagues.count()
        leagues.update(is_archived=False)
        season.allows_new_leagues = True
        season.next_detected_at = None
        season.next_complete_notified_at = None
        season.save(update_fields=['allows_new_leagues', 'next_detected_at', 'next_complete_notified_at'])
        return Response({'detail': f'Unarchived {count} league(s) for Season {season_number}.'})


# ── Admin: Progress to Next Season ───────────────────────────────────────────

class AdminProgressSeasonView(APIView):
    """
    POST /api/v1/admin/progress-season/

    Atomically transitions from the current active season to the next:
      1. Archives all remaining leagues for the current season.
      2. Sets allows_new_leagues=False and is_active=False on the current season.
      3. Syncs the next season from the survivoR dataset (sets is_active=True on it).

    Requires that next_detected_at is set on the active season (i.e., the daily
    probe has confirmed that next-season data exists in the dataset).
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        from django.utils import timezone
        from apps.scoring.tasks import _sync_season

        active_season = Season.objects.filter(is_active=True, version='US').first()
        if active_season is None:
            return Response({'detail': 'No active season found.'}, status=status.HTTP_400_BAD_REQUEST)

        if active_season.next_detected_at is None:
            return Response(
                {'detail': 'No next season data detected yet. Wait for the daily sync to find it.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        next_num = active_season.season_number + 1

        # Archive any remaining live leagues
        leagues = League.objects.filter(season=active_season)
        league_count = leagues.count()
        leagues.update(
            is_archived=True,
            draft_force_open=False,
            draft_close_at=timezone.now(),
        )

        # Lock out new league creation and deactivate the old season
        active_season.allows_new_leagues = False
        active_season.is_active = False
        active_season.save(update_fields=['allows_new_leagues', 'is_active'])

        # Sync the new season — _sync_season sets is_active=True on the new season
        try:
            _sync_season(next_num)
        except Exception as exc:
            logger.exception('AdminProgressSeasonView: failed to sync S%d', next_num)
            return Response(
                {'detail': f'Leagues archived but sync of Season {next_num} failed: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'detail': f'Progressed from Season {active_season.season_number} to Season {next_num}.',
            'archived_leagues': league_count,
            'new_active_season': next_num,
        })


# ── Admin: Score all unscored past episodes ───────────────────────────────────

class AdminScoreUnscoredView(APIView):
    """
    POST /api/v1/admin/score-unscored/{season_number}/

    Finds every episode for the season whose air_date <= today and scored_at
    is null, then calls score_episode() for each one in order.  Returns a
    per-episode summary and a total count.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, season_number):
        from django.utils import timezone
        from apps.castaways.models import Episode
        from apps.scoring.engine import score_episode
        from apps.scoring.data_loader import DataNotReadyError

        today = timezone.now().date()
        unscored = Episode.objects.filter(
            season__season_number=season_number,
            season__version='US',
            scored_at__isnull=True,
            air_date__lte=today,
        ).order_by('episode_number')

        if not unscored.exists():
            return Response({'detail': 'No unscored episodes found.', 'episodes': []})

        results = []
        for episode in unscored:
            try:
                score_episode(season_number, episode.episode_number)
                results.append({
                    'episode_number': episode.episode_number,
                    'status': 'scored',
                })
            except DataNotReadyError as e:
                results.append({
                    'episode_number': episode.episode_number,
                    'status': 'skipped',
                    'reason': f'Data not ready: {e}',
                })
            except Exception as e:
                results.append({
                    'episode_number': episode.episode_number,
                    'status': 'error',
                    'reason': str(e),
                })

        scored_count = sum(1 for r in results if r['status'] == 'scored')
        return Response({
            'episodes_attempted': len(results),
            'episodes_scored': scored_count,
            'episodes': results,
        })


# ── Admin: Castaways list ─────────────────────────────────────────────────────

class AdminCastawaysView(APIView):
    """
    GET /api/v1/admin/castaways/<season_number>/

    Returns all castaways for a season with their alias and image info.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request, season_number):
        castaways = (
            Castaway.objects
            .filter(season__season_number=season_number, season__version='US')
            .order_by('name')
        )
        data = [
            {
                'castaway_id': c.castaway_id,
                'name': c.name,
                'alias': c.alias,
                'display_name': c.display_name,
                'image_url': c.image_url,
                'is_eliminated': c.is_eliminated,
                'original_tribe': c.original_tribe,
                'tribe_color': c.tribe_color,
            }
            for c in castaways
        ]
        return Response(data)


# ── Admin: Update castaway alias (+ optional image re-fetch) ──────────────────

class AdminCastawayAliasView(APIView):
    """
    PATCH /api/v1/admin/castaways/<castaway_id>/alias/

    Body: { "alias": "Display Name", "refetch_image": true }

    Updates the alias.  If refetch_image is true (or image_url is empty),
    clears the existing image_url and re-fetches from Fandom using the new alias.
    """
    permission_classes = [IsSuperAdmin]

    def patch(self, request, castaway_id):
        from apps.castaways.wiki_images import fetch_fandom_image

        castaway = get_object_or_404(Castaway, castaway_id=castaway_id)

        new_alias = request.data.get('alias', '').strip()
        refetch = bool(request.data.get('refetch_image', False))

        castaway.alias = new_alias
        update_fields = ['alias']

        if refetch or not castaway.image_url:
            lookup = new_alias or castaway.name
            img_url = fetch_fandom_image(lookup)
            castaway.image_url = img_url
            update_fields.append('image_url')

        castaway.save(update_fields=update_fields)

        return Response({
            'castaway_id': castaway.castaway_id,
            'name': castaway.name,
            'alias': castaway.alias,
            'display_name': castaway.display_name,
            'image_url': castaway.image_url,
        })
