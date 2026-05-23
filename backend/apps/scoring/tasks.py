import logging
from datetime import date

import pandas as pd
import requests
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = 'https://raw.githubusercontent.com/doehm/survivoR/master/dev/json'


def _fetch_json(table: str) -> pd.DataFrame:
    from io import StringIO
    url = f'{BASE_URL}/{table}.json'
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return pd.read_json(StringIO(r.text))


def _filter_us_season(df: pd.DataFrame, season_number: int) -> pd.DataFrame:
    if 'version' in df.columns:
        df = df[df['version'] == 'US']
    elif 'version_season' in df.columns:
        df = df[df['version_season'].str.startswith('US')]
    if 'season' in df.columns:
        df = df[df['season'] == season_number]
    return df.copy()


def _sync_season(season_number: int) -> None:
    from apps.castaways.models import Season, Castaway, Episode

    # ── Sync castaways ─────────────────────────────────────────────────────────
    # survivoR JSON schema: version, version_season, season, full_name,
    # castaway_id, castaway (first name), age, city, state, episode (boot ep),
    # day, order, result, place, original_tribe, jury, finalist, winner
    raw_castaways = _fetch_json('castaways')
    us_castaways = _filter_us_season(raw_castaways, season_number)

    if us_castaways.empty:
        logger.warning('No castaway data found for season %d', season_number)
        return

    # Load castaway_details for occupation (keyed by castaway_id, one row per person)
    occupation_map: dict[str, str] = {}
    try:
        details = _fetch_json('castaway_details')
        if 'castaway_id' in details.columns and 'occupation' in details.columns:
            occupation_map = details.set_index('castaway_id')['occupation'].dropna().astype(str).to_dict()
    except Exception:
        logger.debug('castaway_details unavailable — occupation will be blank')

    # Build original-tribe → hex color map for this season
    tribe_color_map: dict[str, str] = {}
    try:
        tc = _fetch_json('tribe_colours')
        us_tc = _filter_us_season(tc, season_number)
        if 'tribe_status' in us_tc.columns:
            original_tribes = us_tc[us_tc['tribe_status'] == 'Original']
            if 'tribe' in original_tribes.columns and 'tribe_colour' in original_tribes.columns:
                tribe_color_map = dict(zip(original_tribes['tribe'], original_tribes['tribe_colour']))
                logger.info('Loaded %d tribe colors for S%d: %s', len(tribe_color_map), season_number, tribe_color_map)
    except Exception:
        logger.debug('tribe_colours unavailable — tribe colors will be blank')

    # Ensure exactly one US season is active at a time before creating/updating.
    Season.objects.filter(version='US').exclude(season_number=season_number).update(is_active=False)
    season_obj, _ = Season.objects.update_or_create(
        season_number=season_number,
        defaults={'name': f'Survivor Season {season_number}', 'version': 'US', 'is_active': True},
    )

    for _, row in us_castaways.iterrows():
        castaway_id = str(row.get('castaway_id', '')).strip()
        if not castaway_id:
            continue

        # full_name is the display name; fall back to first-name 'castaway' column
        name = str(row.get('full_name') or row.get('castaway', '')).strip()

        # Combine city + state into hometown
        city = str(row.get('city') or '').strip()
        state = str(row.get('state') or '').strip()
        hometown = ', '.join(filter(None, [city, state]))

        occupation = occupation_map.get(castaway_id, '')

        # result is None for castaways still in the game; non-None for those who left
        result_raw = row.get('result')
        result = str(result_raw).lower() if pd.notna(result_raw) and result_raw is not None else ''
        is_eliminated = bool(result) and any(
            k in result for k in ('voted out', 'quit', 'removed', 'medevac', 'evacuated')
        )

        boot_ep = row.get('episode')
        boot_ep = int(boot_ep) if pd.notna(boot_ep) and boot_ep is not None else None

        original_tribe_val = str(row.get('original_tribe') or '').strip()

        castaway_obj, _ = Castaway.objects.update_or_create(
            castaway_id=castaway_id,
            defaults={
                'season': season_obj,
                'name': name,
                'age': int(row['age']) if 'age' in row and pd.notna(row.get('age')) else None,
                'hometown': hometown,
                'occupation': occupation,
                'original_tribe': original_tribe_val,
                'tribe_color': tribe_color_map.get(original_tribe_val, ''),
                'is_eliminated': is_eliminated,
                'eliminated_episode': boot_ep if is_eliminated else None,
            },
        )

        if not castaway_obj.image_url:
            from apps.castaways.wiki_images import fetch_fandom_image
            # Use the alias (if set) for the Fandom lookup — aliases match the wiki page name
            lookup_name = castaway_obj.alias or name
            img_url = fetch_fandom_image(lookup_name)
            if img_url:
                castaway_obj.image_url = img_url
                castaway_obj.save(update_fields=['image_url'])

    # ── Sync episodes ──────────────────────────────────────────────────────────
    # survivoR JSON schema: version, season, episode (number), episode_date, ...
    raw_episodes = _fetch_json('episodes')
    us_episodes = _filter_us_season(raw_episodes, season_number)

    ep2_air_date = None
    for _, row in us_episodes.iterrows():
        # 'episode' is the per-season episode number in survivoR JSON
        ep_num_raw = row.get('episode') or row.get('episode_number')
        if not pd.notna(ep_num_raw):
            continue
        ep_num = int(ep_num_raw)

        # 'episode_date' is the air date column in survivoR JSON
        air_date_raw = row.get('episode_date') or row.get('air_date')
        if not pd.notna(air_date_raw):
            continue
        air_date = pd.to_datetime(air_date_raw).date()

        Episode.objects.update_or_create(
            season=season_obj,
            episode_number=ep_num,
            defaults={'air_date': air_date},
        )

        if ep_num == 2:
            ep2_air_date = air_date

    if ep2_air_date and not season_obj.draft_lock_date:
        season_obj.draft_lock_date = ep2_air_date
        season_obj.save(update_fields=['draft_lock_date'])
        logger.info('Set draft_lock_date for S%d to %s', season_number, ep2_air_date)

    # ── Set is_merge flag ──────────────────────────────────────────────────────
    try:
        tm = _fetch_json('tribe_mapping')
        us_tm = _filter_us_season(tm, season_number)
        merged_rows = us_tm[us_tm['tribe_status'] == 'Merged'] if 'tribe_status' in us_tm.columns else pd.DataFrame()
        Episode.objects.filter(season=season_obj).update(is_merge=False)
        if not merged_rows.empty:
            merge_ep_num = int(merged_rows['episode'].min())
            Episode.objects.filter(season=season_obj, episode_number=merge_ep_num).update(is_merge=True)
            logger.info('Set is_merge=True for S%d E%d', season_number, merge_ep_num)
    except Exception:
        logger.warning('Could not determine merge episode for season %d', season_number)

    # ── Set is_finale flag ─────────────────────────────────────────────────────
    try:
        Episode.objects.filter(season=season_obj).update(is_finale=False)
        finale_ep_nums = us_episodes[us_episodes['episode_label'] == 'Finale']['episode'].tolist()
        if finale_ep_nums:
            Episode.objects.filter(
                season=season_obj,
                episode_number__in=[int(n) for n in finale_ep_nums],
            ).update(is_finale=True)
            logger.info('Set is_finale=True for S%d episodes %s', season_number, finale_ep_nums)
    except Exception:
        logger.warning('Could not determine finale episode for season %d', season_number)

    logger.info(
        'Synced season %d: %d castaways, %d episodes',
        season_number, len(us_castaways), len(us_episodes),
    )


def _probe_next_season(active_season) -> None:
    """
    Check whether castaways for active_season.season_number+1 have appeared in the
    survivoR dataset.  Sends email notifications on first detection and when the cast
    looks complete (≥ COMPLETE_THRESHOLD castaways).  Does nothing if both notifications
    have already been sent.
    """
    from django.utils import timezone
    from apps.scoring.emails import notify_next_season_detected, notify_next_season_complete

    COMPLETE_THRESHOLD = 18
    next_num = active_season.season_number + 1

    # Nothing left to check — both notifications already sent
    if (active_season.next_detected_at is not None
            and active_season.next_complete_notified_at is not None):
        return

    try:
        raw = _fetch_json('castaways')
        next_rows = _filter_us_season(raw, next_num)
    except Exception:
        logger.debug('_probe_next_season: could not fetch castaways for S%d', next_num)
        return

    if next_rows.empty:
        return

    count = len(next_rows)
    update_fields = []

    if active_season.next_detected_at is None:
        active_season.next_detected_at = timezone.now()
        update_fields.append('next_detected_at')
        logger.info('Next season S%d detected: %d castaway(s)', next_num, count)
        notify_next_season_detected(active_season.season_number, next_num, count)

    if active_season.next_complete_notified_at is None and count >= COMPLETE_THRESHOLD:
        active_season.next_complete_notified_at = timezone.now()
        update_fields.append('next_complete_notified_at')
        logger.info('Next season S%d cast complete: %d castaway(s)', next_num, count)
        notify_next_season_complete(active_season.season_number, next_num, count)

    if update_fields:
        active_season.save(update_fields=update_fields)


@shared_task(name='apps.scoring.tasks.sync_season_data')
def sync_season_data() -> None:
    from apps.castaways.models import Season as SeasonModel
    active_season = SeasonModel.objects.filter(is_active=True, version='US').first()
    if active_season is None:
        logger.warning('sync_season_data: no active US season found in DB, skipping')
        return
    season_number = active_season.season_number
    logger.info('Syncing season %d', season_number)
    try:
        _sync_season(season_number)
    except Exception:
        logger.exception('sync_season_data failed for season %d', season_number)
        raise
    _probe_next_season(active_season)


@shared_task(name='apps.scoring.tasks.score_active_season')
def score_active_season() -> None:
    from apps.castaways.models import Season, Episode
    from apps.scoring.engine import score_episode
    from apps.scoring.data_loader import DataNotReadyError

    try:
        season = Season.objects.get(is_active=True, version='US')
    except Season.DoesNotExist:
        logger.warning('No active US season found')
        return

    today = date.today()
    episodes = Episode.objects.filter(
        season=season,
        air_date__lte=today,
        scored_at__isnull=True,
    ).order_by('episode_number')

    for episode in episodes:
        try:
            score_episode(season.season_number, episode.episode_number)
        except DataNotReadyError as e:
            logger.warning('Data not ready for %s: %s', episode, e)
        except Exception:
            logger.exception('Failed to score %s', episode)
