import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FANDOM_BASE = 'https://survivor.fandom.com/wiki'
HEADERS = {'User-Agent': 'SurvivorPool/1.0 (fantasy game)'}


def fetch_fandom_image(name: str) -> str:
    """
    Fetch a castaway's headshot URL from survivor.fandom.com.
    Returns the image URL string, or '' on any failure.
    """
    wiki_slug = name.strip().replace(' ', '_')
    url = f'{FANDOM_BASE}/{wiki_slug}'
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        if r.status_code != 200:
            logger.debug('Wiki page not found for %s (status %s)', name, r.status_code)
            return ''
        soup = BeautifulSoup(r.text, 'lxml')
        img = soup.select_one('figure.pi-image img')
        if not img:
            logger.debug('No infobox image found for %s', name)
            return ''
        src = img.get('src') or img.get('data-src') or ''
        if not src:
            return ''
        # Normalize fandom CDN URL to a fixed width.
        # Raw src: https://static.wikia.nocookie.net/.../File.jpg/revision/latest/scale-to-width-down/350?cb=...
        base = re.split(r'/revision/latest', src)[0]
        return f'{base}/revision/latest/scale-to-width-down/300'
    except Exception:
        logger.warning('Failed to fetch wiki image for %s', name, exc_info=True)
        return ''
