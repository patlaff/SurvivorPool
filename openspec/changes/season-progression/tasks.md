# Tasks: Season Progression

## Task 1 — Add fields to `Season` model and migrate

**File:** `backend/apps/castaways/models.py`

- [x] Add to `Season`:
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
      help_text='Set when the "cast complete" notification has been sent.',
  )
  ```
- [x] Run `makemigrations castaways` + `migrate` in container
- [x] Copy migration file back to host

Test: `Season.objects.first().allows_new_leagues` returns `True`.

---

## Task 2 — Gmail SMTP settings

**File:** `backend/config/settings.py`

- [x] Add below the existing email-adjacent settings:
  ```python
  EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
  EMAIL_HOST = 'smtp.gmail.com'
  EMAIL_PORT = 587
  EMAIL_USE_TLS = True
  EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
  EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
  DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
  ```

**File:** `.env` (live server)

- [ ] Add (do NOT commit):
  ```
  EMAIL_HOST_USER=patlaff728@gmail.com
  EMAIL_HOST_PASSWORD=<16-char gmail app password>
  ```

**File:** `.env.example`

- [x] Add email vars and annotate `ACTIVE_SEASON`
- [x] Hot-patch settings.py + restart backend

Test: `docker compose exec backend python -c "from django.core.mail import send_mail; send_mail('test', 'test', 'patlaff728@gmail.com', ['patlaff728@gmail.com'])"` sends without error.

---

## Task 3 — Email notification helpers

**File:** `backend/apps/scoring/emails.py` (new file)

- [x] Create with `notify_next_season_detected` and `notify_next_season_complete` functions (see design.md)
- [x] Hot-patch into container

Test: import succeeds in `docker compose exec backend python -c "from apps.scoring.emails import notify_next_season_detected"`.

---

## Task 4 — DB-driven `sync_season_data` task + next-season probe

**File:** `backend/apps/scoring/tasks.py`

- [x] In `sync_season_data`, replace:
  ```python
  season_number = settings.ACTIVE_SEASON
  logger.info('Syncing season %d', season_number)
  try:
      _sync_season(season_number)
  except Exception:
      logger.exception('sync_season_data failed for season %d', season_number)
      raise
  ```
  With:
  ```python
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
  ```
- [x] Add `_probe_next_season(active_season)` function (see design.md)
- [x] Hot-patch + restart celery and celerybeat containers

Test: `docker compose exec backend python -c "from apps.scoring.tasks import sync_season_data; sync_season_data.run()"` runs without error and logs the active season number.

---

## Task 5 — `AdminProgressSeasonView` replaces `AdminArchiveSeasonView`

**File:** `backend/apps/admin_panel/views.py`

- [x] Kept `AdminArchiveSeasonView` (State 1 use) and updated it to also set `allows_new_leagues=False`
- [x] Add `AdminProgressSeasonView` class (see design.md)

**File:** `backend/apps/admin_panel/urls.py`

- [x] Add `AdminProgressSeasonView` import and:
  ```python
  path('admin/progress-season/', AdminProgressSeasonView.as_view(), name='admin-progress-season'),
  ```
- [x] Hot-patch both files + restart backend

Test: `POST /api/v1/admin/progress-season/` with no detected next season returns 400 "No next season data detected yet."

---

## Task 6 — Season serializer: expose new fields

**File:** `backend/apps/castaways/serializers.py`

- [x] Add `'allows_new_leagues'` and `'next_detected_at'` to the `SeasonSerializer` fields tuple
- [x] Hot-patch + restart backend

Test: `GET /api/v1/info/` response includes `allows_new_leagues: true` and `next_detected_at: null`.

---

## Task 7 — TypeScript `Season` interface additions

**File:** `frontend/src/api/info.ts`

- [x] Add to the `Season` interface:
  ```typescript
  allows_new_leagues: boolean
  next_detected_at: string | null
  ```

---

## Task 8 — Admin API: swap `useArchiveSeason` for `useProgressSeason`

**File:** `frontend/src/api/admin.ts`

- [x] Kept `useArchiveSeason` (still used for State 1 archive)
- [x] Add `useProgressSeason` (see design.md): POSTs to `/admin/progress-season/`, invalidates `leagues`, `active-season`, and `admin-leagues` query keys on success

---

## Task 9 — Admin panel: three-state season progression widget

**File:** `frontend/src/pages/AdminPage.tsx`

- [x] Add `useProgressSeason` import alongside existing `useArchiveSeason`
- [x] Replace the archive card in `ScoringTab` with inline three-state progression widget:

  **State determination:**
  ```typescript
  const { data: adminLeagues } = useAdminLeagues()
  const activeSeason = activeSeasonData?.season
  const activeSeasonNumber = activeSeason?.season_number ?? 0
  const hasLiveLeagues = adminLeagues?.some(
    l => !l.is_archived  // any league that isn't archived yet
  ) ?? false
  const nextDetectedAt = activeSeason?.next_detected_at ?? null
  const nextNum = activeSeasonNumber + 1
  ```

  **State 1** — `hasLiveLeagues` is true:
  ```tsx
  <div className="card mb-6 flex items-center justify-between gap-4">
    <div>
      <h2 className="font-semibold text-red-700">Archive Season {activeSeasonNumber}</h2>
      <p className="text-sm text-gray-500 mt-0.5">
        Closes all drafts and marks every league read-only. Do this after the finale.
      </p>
      {archiveMsg && <p className={`text-sm mt-1 ...`}>{archiveMsg}</p>}
    </div>
    {/* confirm step identical to the existing archive button */}
  </div>
  ```
  (For State 1, keep the existing archive behavior from season-lifecycle but now it only archives — it does NOT progress. The "progress" step comes later via the backend's new endpoint.)

  **State 2** — `!hasLiveLeagues && !nextDetectedAt`:
  ```tsx
  <div className="card mb-6">
    <p className="text-sm font-medium text-gray-500">⏳ Watching for Season {nextNum} data…</p>
    <p className="text-xs text-gray-400 mt-1">The daily sync checks automatically. You'll get an email when it appears.</p>
  </div>
  ```

  **State 3** — `!hasLiveLeagues && nextDetectedAt`:
  ```tsx
  <div className="card mb-6 flex items-center justify-between gap-4">
    <div>
      <h2 className="font-semibold text-green-700">Season {nextNum} data detected</h2>
      <p className="text-sm text-gray-500 mt-0.5">
        Detected {new Date(nextDetectedAt).toLocaleDateString()}. Ready to activate.
      </p>
      {progressMsg && <p className={`text-sm mt-1 ...`}>{progressMsg}</p>}
    </div>
    <div className="flex flex-col items-end gap-2 shrink-0">
      {!pendingProgress ? (
        <button className="btn-primary text-sm" onClick={() => setPendingProgress(true)}>
          Progress from Season {activeSeasonNumber} → {nextNum}
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-700">
            This will archive all Season {activeSeasonNumber} leagues and activate Season {nextNum}.
          </span>
          <button className="..." onClick={handleProgress} disabled={progressSeason.isPending}>
            {progressSeason.isPending ? 'Progressing…' : 'Confirm'}
          </button>
          <button className="..." onClick={() => setPendingProgress(false)}>Cancel</button>
        </div>
      )}
    </div>
  </div>
  ```

- [x] Wire up `handleProgress` to call `progressSeason.mutateAsync()`
- [x] Shared `pendingAction` state used across all three states

---

## Task 10 — Dashboard: guard "New League" and "Join League" on `allows_new_leagues`

**File:** `frontend/src/pages/DashboardPage.tsx`

- [x] Add `useActiveSeason` import from `../api/info`
- [x] Derive `canCreateLeague` from `allows_new_leagues`
- [x] Wrap both action buttons and form panels conditionally on `canCreateLeague`

---

## Task 11 — Rebuild and redeploy frontend

- [x] `docker compose build frontend && docker compose up -d frontend`

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — Season model + migration | — |
| 2 — Gmail SMTP settings | — |
| 3 — Email helpers | 2 |
| 4 — DB-driven sync + probe | 1, 3 |
| 5 — AdminProgressSeasonView | 1 |
| 6 — Season serializer | 1 |
| 7 — TS Season interface | 6 |
| 8 — useProgressSeason hook | 5 |
| 9 — Admin panel widget | 7, 8 |
| 10 — Dashboard guard | 7 |
| 11 — Build + deploy | 9, 10 |
