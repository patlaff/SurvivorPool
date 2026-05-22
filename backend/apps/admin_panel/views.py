import json
import os
import tempfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.castaways.models import Season
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
                'is_test': league.is_test,
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
                        'castaway_name': ev.castaway.name,
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
                    'name': v['castaway'].name,
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
