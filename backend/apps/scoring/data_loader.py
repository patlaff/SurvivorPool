import logging
import pickle
import time
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = 'https://raw.githubusercontent.com/doehm/survivoR/master/dev/json'
CACHE_DIR = Path('/tmp/survivorpool_cache')
CACHE_TTL_SECONDS = 23 * 3600

# All tables available as JSON in the survivoR repo.
# advantage_movement may lag a few episodes behind during an airing season —
# detectors handle empty DataFrames gracefully.
TABLES = [
    'advantage_movement',
    'advantage_details',
    'vote_history',
    'challenge_results',
    'castaways',
    'castaway_details',
    'boot_mapping',
    'episodes',
    'jury_votes',
    'journeys',
]

KNOWN_IDOL_TYPES = {
    'Hidden Immunity Idol',
    'Hidden Immunity Idol (idol nullifier)',
    'Immunity Idol',
}

KNOWN_ADVANTAGE_TYPES = {
    'Extra Vote',
    'Steal-a-Vote',
    'Steal a Vote',
    'Knowledge is Power',
    'Amulet',
    'Shot in the Dark',
}


class DataNotReadyError(Exception):
    def __init__(self, episode: int):
        self.episode = episode
        super().__init__(f'Data not ready for episode {episode}')


def _cache_path(table: str, season: int) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f'{table}_US{season}.pkl'


def _is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > CACHE_TTL_SECONDS


def _fetch(table: str) -> pd.DataFrame:
    from io import StringIO
    url = f'{BASE_URL}/{table}.json'
    logger.info('Fetching %s', url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return pd.read_json(StringIO(response.text))


def load_tables(season: int, refresh: bool = False) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}

    for table in TABLES:
        path = _cache_path(table, season)

        if not refresh and not _is_stale(path):
            with open(path, 'rb') as f:
                df = pickle.load(f)
            result[table] = df
            continue

        try:
            raw = _fetch(table)
        except Exception:
            logger.warning('Could not fetch %s — skipping', table)
            result[table] = pd.DataFrame()
            continue

        # Filter to US version
        if 'version' in raw.columns:
            raw = raw[raw['version'] == 'US'].copy()
        elif 'version_season' in raw.columns:
            raw = raw[raw['version_season'].str.startswith('US')].copy()

        # Filter to the requested season
        if 'season' in raw.columns:
            raw = raw[raw['season'] == season].copy()
        elif 'version_season' in raw.columns:
            raw = raw[raw['version_season'] == f'US{season}'].copy()

        with open(path, 'wb') as f:
            pickle.dump(raw, f)

        result[table] = raw

    return result


def check_episode_ready(tables: dict[str, pd.DataFrame], episode_number: int) -> None:
    episodes = tables.get('episodes', pd.DataFrame())
    if episodes.empty:
        raise DataNotReadyError(episode_number)
    # survivoR JSON uses 'episode' for the episode number column
    ep_col = 'episode' if 'episode' in episodes.columns else 'episode_number'
    if ep_col not in episodes.columns:
        raise DataNotReadyError(episode_number)
    if episode_number not in episodes[ep_col].values:
        raise DataNotReadyError(episode_number)
