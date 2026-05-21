import json
import logging
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.castaways.models import Episode
from apps.leagues.models import Perk, Roster
from apps.scoring.data_loader import DataNotReadyError, check_episode_ready, load_tables
from apps.scoring.event_detector import detect_all_events
from apps.scoring.models import PlayerEpisodeScore, ScoringEvent

logger = logging.getLogger(__name__)


def _load_config() -> dict[str, int]:
    path = Path(getattr(settings, 'SCORING_CONFIG_PATH', settings.BASE_DIR.parent / 'scoring_config.json'))
    with open(path) as f:
        return json.load(f)


def score_episode(season_number: int, episode_number: int) -> None:
    tables = load_tables(season_number, refresh=True)
    check_episode_ready(tables, episode_number)

    config = _load_config()
    events = detect_all_events(tables, episode_number)

    episode = Episode.objects.get(
        season__season_number=season_number,
        episode_number=episode_number,
    )

    # Upsert ScoringEvent rows
    for castaway_id_or_name, ep_num, event_name in events:
        points = config.get(event_name)
        if points is None:
            logger.warning('Unknown event %r — skipping', event_name)
            continue

        try:
            from apps.castaways.models import Castaway
            try:
                castaway = Castaway.objects.get(castaway_id=castaway_id_or_name, season__season_number=season_number)
            except Castaway.DoesNotExist:
                castaway = Castaway.objects.get(name=castaway_id_or_name, season__season_number=season_number)
        except Castaway.DoesNotExist:
            logger.warning('Castaway not found: %r season %d', castaway_id_or_name, season_number)
            continue

        ScoringEvent.objects.update_or_create(
            castaway=castaway,
            episode=episode,
            event_name=event_name,
            defaults={'points': points},
        )

    # Score each roster
    rosters = Roster.objects.filter(
        league__season__season_number=season_number,
        league__season__version='US',
    ).prefetch_related('slots__castaway', 'perks')

    for roster in rosters:
        castaway_ids = list(roster.slots.values_list('castaway_id', flat=True))
        raw_points = sum(
            ScoringEvent.objects.filter(
                castaway_id__in=castaway_ids,
                episode=episode,
            ).values_list('points', flat=True)
        )

        multiplier = Decimal('1.0')
        try:
            boost = roster.perks.get(perk_type=Perk.BOOST, used=True, boost_target_episode=episode_number)
            multiplier = Decimal('2.0')
        except Perk.DoesNotExist:
            pass

        final_points = int(raw_points * multiplier)

        PlayerEpisodeScore.objects.update_or_create(
            roster=roster,
            episode=episode,
            defaults={
                'raw_points': raw_points,
                'multiplier': multiplier,
                'final_points': final_points,
            },
        )

    episode.scored_at = timezone.now()
    episode.save(update_fields=['scored_at'])
    logger.info('Scored S%dE%d: %d events, %d rosters', season_number, episode_number, len(events), rosters.count())
