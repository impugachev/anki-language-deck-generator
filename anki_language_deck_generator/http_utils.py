"""Shared HTTP helpers: a descriptive User-Agent and GET with retry/backoff."""
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from anki_language_deck_generator.version import __version__

# Wikimedia (and other services) ask for a User-Agent that identifies the tool
# and gives a contact; spoofed browser agents get the strictest rate limits.
USER_AGENT = (
    f'AnkiLanguageDeckGenerator/{__version__} '
    '(https://github.com/impugachev/anki-language-deck-generator)'
)
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
DEFAULT_TIMEOUT = 30


def make_session():
    """A requests session with the descriptive User-Agent, shared by all fetchers."""
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    return session


def _retry_after_seconds(response):
    """Parse the Retry-After header (seconds or HTTP-date); None if absent or invalid."""
    value = response.headers.get('Retry-After')
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def get_with_retry(session, url, *, attempts=4, max_wait=90, **kwargs):
    """GET `url`, retrying on 429/5xx responses and on connection errors.

    Waits for the Retry-After header when present (capped at `max_wait`
    seconds), otherwise backs off exponentially (1, 2, 4, ... s). Returns the
    last response; the caller decides what to do with non-retryable statuses
    such as 404. A connection error on the last attempt is raised.
    """
    kwargs.setdefault('timeout', DEFAULT_TIMEOUT)
    backoff = 1
    for attempt in range(1, attempts + 1):
        last_attempt = attempt == attempts
        try:
            response = session.get(url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as e:
            if last_attempt:
                raise
            wait = min(backoff, max_wait)
            logging.warning(
                f'{type(e).__name__} for {url}, retrying in {wait}s ({attempt}/{attempts - 1})'
            )
        else:
            if response.status_code not in RETRY_STATUS_CODES or last_attempt:
                return response
            wait = _retry_after_seconds(response)
            if wait is None:
                wait = backoff
            wait = min(wait, max_wait)
            logging.warning(
                f'HTTP {response.status_code} from {url}, waiting {wait:.0f}s before retry '
                f'({attempt}/{attempts - 1})'
            )
        time.sleep(wait)
        backoff *= 2
