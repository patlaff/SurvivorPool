# Design: Join Code Brute-Force Lockout

## Redis keys (per user)

| Key | Value | TTL |
|-----|-------|-----|
| `join_fail:{user_id}` | integer failure count | 86 400 s (24 h rolling window) |
| `join_lockout_until:{user_id}` | Unix timestamp (float) | = lockout duration |

On success, both keys are deleted.

## Lockout formula

```python
import math

LOCKOUT_THRESHOLD = 5  # first lockout after this many failures

def lockout_seconds(failures: int) -> int:
    """Returns 0 when below threshold. Grows logarithmically above it."""
    if failures < LOCKOUT_THRESHOLD:
        return 0
    return round(30 * math.log2(failures - 3))
```

Sample values:

| failures | delay |
|----------|-------|
| < 5 | 0 s |
| 5 | 30 s |
| 7 | 60 s |
| 11 | 90 s |
| 19 | 120 s |
| 35 | 150 s |
| 67 | 180 s |

The curve grows slowly by design. A script trying one attempt per window would take over an hour to reach 100 failures; a human who mistyped four times in a row faces no restriction at all.

## Helper module — `apps/leagues/join_lockout.py`

```python
import math
import time
import redis as redis_lib
from django.conf import settings

LOCKOUT_THRESHOLD = 5
FAIL_TTL = 86_400  # 24 h

def _redis():
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)

def lockout_seconds(failures: int) -> int:
    if failures < LOCKOUT_THRESHOLD:
        return 0
    return round(30 * math.log2(failures - 3))

def check_lockout(user_id: int) -> float:
    """Return seconds remaining in lockout, or 0 if not locked out."""
    r = _redis()
    until = r.get(f'join_lockout_until:{user_id}')
    if until is None:
        return 0.0
    remaining = float(until) - time.time()
    return max(0.0, remaining)

def record_failure(user_id: int) -> int:
    """Increment failure count, set lockout if threshold crossed. Returns new count."""
    r = _redis()
    key = f'join_fail:{user_id}'
    count = r.incr(key)
    r.expire(key, FAIL_TTL)
    delay = lockout_seconds(count)
    if delay > 0:
        until = time.time() + delay
        r.set(f'join_lockout_until:{user_id}', until, ex=delay + 5)
    return count

def clear_lockout(user_id: int) -> None:
    """Call on successful join to reset the counter."""
    r = _redis()
    r.delete(f'join_fail:{user_id}', f'join_lockout_until:{user_id}')
```

`REDIS_URL` is already set in `settings.py` as `os.environ.get('REDIS_URL', 'redis://redis:6379/0')`.

## View changes — `LeagueJoinByCodeView`

```python
from .join_lockout import check_lockout, record_failure, clear_lockout

class LeagueJoinByCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        invite_code = request.data.get('invite_code', '').strip()
        if not invite_code:
            return Response({'detail': 'Provide an invite_code.'}, status=400)

        # ── Lockout check ────────────────────────────────────────────────────
        remaining = check_lockout(request.user.id)
        if remaining > 0:
            return Response(
                {'detail': 'Too many failed attempts.', 'retry_after': math.ceil(remaining)},
                status=429,
            )

        # ── Code lookup ──────────────────────────────────────────────────────
        try:
            league = League.objects.get(invite_code=invite_code)
        except League.DoesNotExist:
            record_failure(request.user.id)
            return Response({'detail': 'Invalid invite code.'}, status=404)

        _, created = Membership.objects.get_or_create(league=league, user=request.user)
        if not created:
            # Already a member — don't count as a brute-force failure
            return Response({'detail': 'Already a member.'}, status=400)

        clear_lockout(request.user.id)
        return Response({'detail': 'Joined successfully.', 'slug': league.slug})
```

Note: `get_object_or_404` is replaced with `League.objects.get` + `except League.DoesNotExist` so we can distinguish a bad code from a server error and record the failure.

## Settings change

Add `REDIS_URL` to `settings.py` as a top-level constant (it's currently only used by Celery):

```python
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
```

This lets `join_lockout.py` read it without importing Celery settings.

## Frontend — `DashboardPage.tsx`

Parse the `retry_after` field from 429 responses and show a specific message:

```typescript
async function handleJoin(e: React.FormEvent) {
  e.preventDefault()
  setError('')
  try {
    await joinLeague.mutateAsync({ invite_code: joinCode })
    setJoinCode('')
    setShowJoin(false)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { status?: number; data?: { retry_after?: number } } }
    if (axiosErr.response?.status === 429) {
      const secs = axiosErr.response.data?.retry_after ?? 30
      setError(`Too many failed attempts. Try again in ${secs}s.`)
    } else {
      setError('Invalid invite code.')
    }
  }
}
```

## Files changed

| File | Change |
|------|--------|
| `backend/config/settings.py` | Add top-level `REDIS_URL` constant |
| `backend/apps/leagues/join_lockout.py` | New file — Redis helper |
| `backend/apps/leagues/views.py` | Check/record/clear lockout in `LeagueJoinByCodeView` |
| `frontend/src/pages/DashboardPage.tsx` | Parse `retry_after` from 429, show countdown message |

No new dependencies. No migrations.
