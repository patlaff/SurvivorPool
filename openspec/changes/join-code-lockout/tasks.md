# Tasks: Join Code Brute-Force Lockout

## Task 1 — Add `REDIS_URL` to settings

**File:** `backend/config/settings.py`

- [x] Add `REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')` as a top-level constant (near the Celery config block, around line 122)

---

## Task 2 — Create `join_lockout.py` helper module

**File:** `backend/apps/leagues/join_lockout.py` (new file)

- [x] Implement `_redis()` — returns a `redis.from_url` client using `settings.REDIS_URL`
- [x] Implement `lockout_seconds(failures)` — returns 0 below threshold, `round(30 * math.log2(failures - 3))` above it
- [x] Implement `check_lockout(user_id)` — reads `join_lockout_until:{user_id}` from Redis, returns seconds remaining (0 if not set or expired)
- [x] Implement `record_failure(user_id)` — increments `join_fail:{user_id}` (24 h TTL), sets `join_lockout_until:{user_id}` if above threshold
- [x] Implement `clear_lockout(user_id)` — deletes both keys on successful join

---

## Task 3 — Update `LeagueJoinByCodeView`

**File:** `backend/apps/leagues/views.py`

- [x] Import `math` and `from .join_lockout import check_lockout, record_failure, clear_lockout`
- [x] At the top of `post()`, call `check_lockout(request.user.id)` and return HTTP 429 with `{'detail': 'Too many failed attempts.', 'retry_after': <ceil'd seconds>}` if locked out
- [x] Replace `get_object_or_404(League, invite_code=invite_code)` with `League.objects.get(invite_code=invite_code)` inside a `try/except League.DoesNotExist`
- [x] In the `DoesNotExist` branch, call `record_failure(request.user.id)` and return HTTP 404
- [x] After `get_or_create` succeeds (new member), call `clear_lockout(request.user.id)`

---

## Task 4 — Update join error handling in the frontend

**File:** `frontend/src/pages/DashboardPage.tsx`

- [x] In `handleJoin`, replace the generic `catch` with one that inspects `err.response.status`
- [x] If status is 429, read `err.response.data.retry_after` and set error to `Too many failed attempts. Try again in Xs.`
- [x] Otherwise, keep the existing `'Invalid invite code.'` message

---

## Task 5 — Rebuild and redeploy

- [x] `docker compose exec backend python -c "from apps.leagues.join_lockout import check_lockout; print(check_lockout(0))"` — smoke-test the new module
- [x] `docker compose build frontend && docker compose up -d frontend`
- [x] `docker compose restart backend`
- [ ] Verify: submitting a wrong code 5 times starts returning 429 with `retry_after`; submitting the right code resets the counter

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — settings.py | — |
| 2 — join_lockout.py | 1 |
| 3 — views.py | 2 |
| 4 — DashboardPage.tsx | — |
| 5 — Rebuild | 3, 4 |
