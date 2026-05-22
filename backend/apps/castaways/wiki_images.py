import logging
import re

import requests

logger = logging.getLogger(__name__)

FANDOM_API = 'https://survivor.fandom.com/api.php'
FANDOM_BASE = 'https://survivor.fandom.com/wiki'
# Use a browser-like UA; Fandom blocks very plain UAs
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (compatible; SurvivorPool/1.0; '
        '+https://github.com/patlaff/SurvivorPool)'
    ),
}


def fetch_fandom_image(name: str) -> str:
    """
    Fetch a castaway's headshot URL from survivor.fandom.com.
    Returns a normalised Wikia CDN URL string, or '' on any failure.

    Strategy:
    1. MediaWiki JSON API — reliable, no HTML parsing, handles redirects,
       immune to lazy-loading (returns thumbnail URL directly).
    2. HTML scrape fallback — in case the API is blocked, looks for the
       portable infobox image, correctly preferring data-src over src
       because Fandom lazy-loads with a base64 placeholder in src.
    """
    wiki_slug = name.strip().replace(' ', '_')
    return _fetch_via_api(wiki_slug) or _fetch_via_html(wiki_slug, name)


def _fetch_via_api(wiki_slug: str) -> str:
    """Use the MediaWiki API to get the page's representative thumbnail."""
    try:
        r = requests.get(
            FANDOM_API,
            params={
                'action': 'query',
                'titles': wiki_slug,
                'prop': 'pageimages',
                'pithumbsize': 300,
                'pilicense': 'any',
                'format': 'json',
            },
            headers=HEADERS,
            timeout=15,
        )
        if r.status_code != 200:
            logger.debug('Fandom API %s for %s', r.status_code, wiki_slug)
            return ''
        pages = r.json().get('query', {}).get('pages', {})
        for page in pages.values():
            src = page.get('thumbnail', {}).get('source', '')
            if src:
                return src
        return ''
    except Exception:
        logger.debug('Fandom API exception for %s', wiki_slug, exc_info=True)
        return ''


def _fetch_via_html(wiki_slug: str, name: str) -> str:
    """
    Fallback: scrape the portable infobox from the wiki page.
    Fandom lazy-loads images — the real URL is in data-src, not src.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning('beautifulsoup4 not installed; skipping HTML fallback')
        return ''

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
        # data-src holds the real URL; src is a 1×1 base64 placeholder
        src = img.get('data-src') or img.get('src') or ''
        if not src or src.startswith('data:'):
            return ''
        # Strip existing size params and request a fixed 300px width
        base = re.split(r'/revision/latest', src)[0]
        return f'{base}/revision/latest/scale-to-width-down/300'
    except Exception:
        logger.warning('Failed to scrape wiki image for %s', name, exc_info=True)
        return ''
