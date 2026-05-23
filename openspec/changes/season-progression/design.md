# Design: Season Progression

## Backend

### 1 — `Season` model additions

**File:** `backend/apps/castaways/models.py`

```python
allows_new_leagues = models.BooleanField(
    default=True,
    help_text='False after leagues are archived; prevents new league creation during the dormant period.',
)
next_detected_at = models.DateTimeField(
    null=True, blank=True,
    help_text='Set when castaways for season_number+1 first appear in the survivoR dataset.',
)
next_complete_notified_at = models.DateTimeField(
    null=True, blank=True,
    help_text='Set when the "cast complete" notification has been sent. Null = not yet sent.',
)
```

Run `makemigrations castaways` + `migrate` and copy the migration to host.

Constants (in `tasks.py` or a settings constant):
```python
NEXT_SEASON_COMPLETE_THRESHOLD = 18  # castaway count considered a full cast
```

---

### 2 — Email utility

**File:** `backend/apps/scoring/emails.py` (new file)

```python
from django.conf import settings
from django.core.mail import send_mail

ADMIN_URL = getattr(settings, 'ADMIN_SITE_URL', 'http://localhost')


def notify_next_season_detected(current_number: int, next_number: int, castaway_count: int) -> None:
    subject = f'[SurvivorPool] Season {next_number} data has appeared'
    body = (
        f'The survivoR dataset now contains {castaway_count} castaway(s) for Season {next_number}.\n\n'
        f'This is the initial detection — the full cast may not be announced yet.\n\n'
        f'Log in to the admin panel when ready:\n{ADMIN_URL}/admin\n'
    )
    send_mail(subject, body, settings.EMAIL_HOST_USER, settings.SUPERADMIN_EMAILS, fail_silently=True)


def notify_next_season_complete(current_number: int, next_number: int, castaway_count: int) -> None:
    subject = f'[SurvivorPool] Season {next_number} cast looks complete ({castaway_count} castaways)'
    body = (
        f'The survivoR dataset now has {castaway_count} castaways for Season {next_number}.\n\n'
        f'The cast appears to be complete. Log in to the admin panel and click\n'
        f'"Progress from Season {current_number} → Season {next_number}" to activate it.\n\n'
        f'{ADMIN_URL}/admin\n'
    )
    send_mail(subject, body, settings.EMAIL_HOST_USER, settings.SUPERADMIN_EMAILS, fail_silently=True)
```

---

### 3 — Django email settings

**File:** `backend/config/settings.py`

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

**File:** `.env` (live server — not committed)
```
EMAIL_HOST_USER=patlaff728@gmail.com
EMAIL_HOST_PASSWORD=<16-char gmail app password>
```

**File:** `.env.example`
```
# Email (Gmail SMTP — generate an App Password at myaccount.google.com/apppasswords)
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# ACTIVE_SEASON is only needed to bootstrap a fresh database.
# Run: docker compose exec backend python manage.py sync_season <N>
# After that, the active season is tracked in the database.
# ACTIVE_SEASON=50
```

---

### 4 — Revised `sync_season_data` task

**File:** `backend/apps/scoring/tasks.py`

Replace:
```python
season_number = settings.ACTIVE_SEASON
```
With:
```python
from apps.castaways.models import Season as SeasonModel
active_season = SeasonModel.objects.filter(is_active=True, version='US').first()
if active_season is None:
    logger.warning('sync_season_data: no active US season found in DB, skipping')
    return
season_number = active_season.season_number
```

After `_sync_season(season_number)` succeeds, call the new probe:
```python
_probe_next_season(active_season)
```

---

### 5 — Next-season probe helper

**File:** `backend/apps/scoring/tasks.py`

```python
def _probe_next_season(active_season) -> None:
    """
    Fetch the survivoR castaways table and check whether data for active_season+1 exists.
    Sends notification emails on first detection and when the cast looks complete.
    Does nothing if the active season already has a progression in flight (next_detected_at set
    and we've already sent the complete notification, or the admin has already progressed).
    """
    from django.utils import timezone
    from apps.scoring.emails import notify_next_season_detected, notify_next_season_complete

    COMPLETE_THRESHOLD = 18
    next_num = active_season.season_number + 1

    try:
        raw = _fetch_json('castaways')
        next_rows = _filter_us_season(raw, next_num)
    except Exception:
        logger.debug('_probe_next_season: could not fetch castaways for S%d', next_num)
        return

    if next_rows.empty:
        return  # nothing yet

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
```

---

### 6 — `AdminProgressSeasonView` (replaces `AdminArchiveSeasonView`)

**File:** `backend/apps/admin_panel/views.py`

Remove `AdminArchiveSeasonView`. Add:

```python
class AdminProgressSeasonView(APIView):
    """
    POST /api/v1/admin/progress-season/

    Atomically:
      1. Closes and archives all leagues for the current active season.
      2. Sets allows_new_leagues=False on the current season.
      3. Deactivates the current season (is_active=False).
      4. Syncs the next season from the survivoR dataset (which activates it).

    The "next season number" is derived as active_season.season_number + 1.
    Returns an error if there is no detected next season yet, or if a sync fails.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        from django.utils import timezone
        from apps.scoring.tasks import _sync_season

        active_season = Season.objects.filter(is_active=True, version='US').first()
        if active_season is None:
            return Response({'detail': 'No active season found.'}, status=status.HTTP_400_BAD_REQUEST)

        if active_season.next_detected_at is None:
            return Response(
                {'detail': 'No next season data detected yet. Wait for the daily sync to find it.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        next_num = active_season.season_number + 1

        # Archive all current leagues
        leagues = League.objects.filter(season=active_season)
        league_count = leagues.count()
        leagues.update(
            is_archived=True,
            draft_force_open=False,
            draft_close_at=timezone.now(),
        )

        # Lock out new league creation and deactivate the old season
        active_season.allows_new_leagues = False
        active_season.is_active = False
        active_season.save(update_fields=['allows_new_leagues', 'is_active'])

        # Sync the new season (this sets is_active=True on next season)
        try:
            _sync_season(next_num)
        except Exception as exc:
            logger.exception('AdminProgressSeasonView: failed to sync S%d', next_num)
            return Response(
                {'detail': f'Leagues archived but sync of Season {next_num} failed: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'detail': f'Progressed from Season {active_season.season_number} to Season {next_num}.',
            'archived_leagues': league_count,
            'new_active_season': next_num,
        })
```

**File:** `backend/apps/admin_panel/urls.py`

Remove the `admin-archive-season` path and import. Add:
```python
path('admin/progress-season/', AdminProgressSeasonView.as_view(), name='admin-progress-season'),
```

---

### 7 — Season serializer: expose new fields

**File:** `backend/apps/castaways/serializers.py`

```python
fields = ('season_number', 'name', 'is_active', 'draft_lock_date',
          'allows_new_leagues', 'next_detected_at')
```

(`next_complete_notified_at` is internal — no need to expose it to the frontend.)

---

## Frontend

### 8 — Admin API: `useProgressSeason` hook

**File:** `frontend/src/api/admin.ts`

Remove `useArchiveSeason`. Add:

```typescript
export function useProgressSeason() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api.post('/admin/progress-season/').then(r => r.data as { detail: string; archived_leagues: number; new_active_season: number }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leagues'] })
      qc.invalidateQueries({ queryKey: ['active-season'] })
    },
  })
}
```

---

### 9 — Admin panel: three-state progression widget

**File:** `frontend/src/pages/AdminPage.tsx`

Replace the archive button block in `ScoringTab` with a `SeasonProgressionWidget` component:

```
State 1 — leagues still active (any non-archived league exists for active season)
  Shows: [ Archive Season N ] with confirm step (existing behavior)

State 2 — dormant, no next data yet (all leagues archived, next_detected_at null)
  Shows: ⏳ Watching for Season N+1 data... (disabled, gray)

State 3 — next data detected (next_detected_at is set)
  Shows: 🔔 Season N+1 data detected on <date>
         [ Progress from Season N → N+1 ] with confirm step
```

The widget derives its state from `activeSeasonData?.season`:
```typescript
const season = activeSeasonData?.season
const hasLiveLeagues = /* fetched from admin leagues data or leaderboard */
const isDetected = !!season?.next_detected_at
const nextNum = (season?.season_number ?? 0) + 1
```

For determining "are there still live leagues", the admin leagues list is already fetched in `LeaguesTab`. Pass it down or expose a count on the active season API response. The simplest approach: check whether `useAdminLeagues` has any leagues with `!is_archived` for the active season.

---

### 10 — Dashboard: hide "New League" when dormant

**File:** `frontend/src/pages/DashboardPage.tsx`

```typescript
const { data: activeSeasonData } = useActiveSeason()
const canCreateLeague = activeSeasonData?.season?.allows_new_leagues ?? false
```

Replace the unconditional "New League" button with:
```tsx
{canCreateLeague && (
  <button onClick={() => setShowCreate(true)} className="btn-primary">+ New League</button>
)}
```

Same guard on the "Join League" button — joining an archived season isn't useful either:
```tsx
{canCreateLeague && (
  <button onClick={() => setShowJoin(true)} className="btn-secondary">Join League</button>
)}
```

---

### 11 — TypeScript: `Season` interface additions

**File:** `frontend/src/api/info.ts` (or wherever the `Season` type is defined)

```typescript
interface Season {
  season_number: number
  name: string
  is_active: boolean
  draft_lock_date: string | null
  allows_new_leagues: boolean
  next_detected_at: string | null  // ISO datetime
}
```

---

## Files Changed

| File | Change |
|------|--------|
| `backend/apps/castaways/models.py` | Add `allows_new_leagues`, `next_detected_at`, `next_complete_notified_at` |
| `backend/apps/castaways/migrations/` | Generated migration |
| `backend/apps/castaways/serializers.py` | Expose `allows_new_leagues`, `next_detected_at` |
| `backend/apps/scoring/tasks.py` | DB-driven sync, add `_probe_next_season` |
| `backend/apps/scoring/emails.py` | New — email notification helpers |
| `backend/config/settings.py` | Gmail SMTP settings |
| `.env` | Add `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` |
| `.env.example` | Add email vars, annotate `ACTIVE_SEASON` as bootstrap-only |
| `backend/apps/admin_panel/views.py` | Replace `AdminArchiveSeasonView` with `AdminProgressSeasonView` |
| `backend/apps/admin_panel/urls.py` | Replace archive URL with progress URL |
| `frontend/src/api/admin.ts` | Replace `useArchiveSeason` with `useProgressSeason` |
| `frontend/src/api/info.ts` | Add `allows_new_leagues`, `next_detected_at` to Season type |
| `frontend/src/pages/AdminPage.tsx` | Three-state season progression widget |
| `frontend/src/pages/DashboardPage.tsx` | Guard "New League" / "Join League" on `allows_new_leagues` |
