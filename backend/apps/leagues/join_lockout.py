import time

import redis as redis_lib
from django.conf import settings

LOCKOUT_THRESHOLD = 5   # failures before first lockout
FAIL_TTL = 86_400       # 24 h rolling window for failure count


def _redis():
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


MAX_LOCKOUT = 3600  # cap at 1 hour


def lockout_seconds(failures: int) -> int:
    """
    Returns the lockout duration in seconds for a given failure count.
    Returns 0 when below the threshold.
    Doubles each failure above the threshold (capped at 1 hour):
      5 → 30 s, 6 → 60 s, 7 → 120 s, 8 → 240 s, 9 → 480 s,
      10 → 960 s (~16 min), 11 → 1920 s (~32 min), 12+ → 3600 s (1 hr)
    """
    if failures < LOCKOUT_THRESHOLD:
        return 0
    return min(30 * (2 ** (failures - LOCKOUT_THRESHOLD)), MAX_LOCKOUT)


def check_lockout(user_id: int) -> float:
    """
    Return the number of seconds remaining in the lockout for this user,
    or 0.0 if the user is not locked out.
    """
    r = _redis()
    until = r.get(f'join_lockout_until:{user_id}')
    if until is None:
        return 0.0
    remaining = float(until) - time.time()
    return max(0.0, remaining)


def record_failure(user_id: int) -> int:
    """
    Increment the failure counter for this user and, if the count crosses
    the threshold, set a lockout key with an appropriate TTL.
    Returns the new failure count.
    """
    r = _redis()
    fail_key = f'join_fail:{user_id}'
    count = r.incr(fail_key)
    r.expire(fail_key, FAIL_TTL)

    delay = lockout_seconds(count)
    if delay > 0:
        until = time.time() + delay
        # Give the lockout key a small extra buffer so it doesn't expire
        # a split-second before the client's retry window closes.
        r.set(f'join_lockout_until:{user_id}', until, ex=delay + 5)

    return count


def clear_lockout(user_id: int) -> None:
    """
    Delete both lockout keys for this user.
    Call this on a successful join to reset the failure counter.
    """
    r = _redis()
    r.delete(f'join_fail:{user_id}', f'join_lockout_until:{user_id}')
