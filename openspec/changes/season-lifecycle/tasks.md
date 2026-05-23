# Tasks: Season Lifecycle Management

## Task 1 — Fix sync task: enforce single active season

**File:** `backend/apps/scoring/tasks.py`

- [x] Immediately before `Season.objects.update_or_create(season_number=season_number, ...)`, add:
  ```python
  Season.objects.filter(version='US').exclude(season_number=season_number).update(is_active=False)
  ```
- [x] Hot-patch + restart backend
- [x] Verify: `Season.objects.filter(is_active=True, version='US').count()` returns 1

Test: After running `sync_season 50`, only season 50 has `is_active=True`. "How to Play" shows Season 50.

---

## Task 2 — Add `is_archived` to `League` model and migrate

**File:** `backend/apps/leagues/models.py`

- [x] Add to `League`:
  ```python
  is_archived = models.BooleanField(
      default=False,
      help_text='True when the season has concluded. League becomes read-only.',
  )
  ```
- [x] Run `makemigrations leagues` + `migrate` in the container
- [x] Copy migration file back to host

Test: `League.objects.first().is_archived` exists and defaults to `False`.

---

## Task 3 — Expose `is_archived` in serializers

**File:** `backend/apps/leagues/serializers.py`

- [x] Add `'is_archived'` to `LeagueSerializer.Meta.fields`
- [x] Add `'is_archived'` to `LeagueDetailSerializer.Meta.fields`
- [x] Hot-patch serializers file + restart backend

Test: `GET /api/v1/leagues/` response includes `is_archived: false` on each league.

---

## Task 4 — Guard write operations on archived leagues

**File:** `backend/apps/leagues/views.py`

- [x] In `DraftView.put`, after the draft-open check, add:
  ```python
  if league.is_archived:
      return Response({'detail': 'This league has been archived and is now read-only.'}, status=status.HTTP_403_FORBIDDEN)
  ```
- [x] Same guard at the top of `SwapPerkView.post` (after `get_object_or_404(Roster, ...)`)
- [x] Same guard at the top of `BoostPerkView.post` (after `get_object_or_404(Roster, ...)`)
- [x] Hot-patch + restart backend

Test: PUT /leagues/<archived-slug>/draft/ → 403 with "archived" message.

---

## Task 5 — Admin "Archive Season" endpoint

**File:** `backend/apps/admin_panel/views.py`

- [x] Add `AdminArchiveSeasonView` class (POST only, `IsSuperAdmin`):
  - Looks up `Season` by `season_number`
  - Bulk-updates all `League` objects for that season: `is_archived=True`, `draft_force_open=False`, `draft_close_at=timezone.now()`
  - Returns `{'detail': 'Archived N league(s) for Season X.'}`

**File:** `backend/apps/admin_panel/urls.py`

- [x] Add: `path('admin/archive-season/<int:season_number>/', AdminArchiveSeasonView.as_view(), name='admin-archive-season')`
- [x] Hot-patch both files + restart backend

Test: `POST /api/v1/admin/archive-season/47/` → leagues for S47 are archived; their drafts are closed.

---

## Task 6 — AdminPage: dynamic active season + Archive button

**File:** `frontend/src/pages/AdminPage.tsx`

- [x] Import `useActiveSeason` from `../api/info`
- [x] Remove `const ACTIVE_SEASON = 50`; instead call `useActiveSeason()` at the top of `AdminPage` and derive:
  ```tsx
  const { data: activeSeasonData } = useActiveSeason()
  const ACTIVE_SEASON = activeSeasonData?.season?.season_number ?? 0
  ```
- [x] Pass `ACTIVE_SEASON` down to `ScoringTab` and `ConfigTab` as a prop (or inline within the same component scope)
- [x] Disable score/rescore buttons when `ACTIVE_SEASON === 0`

**File:** `frontend/src/api/admin.ts`

- [x] Add `useArchiveSeason` mutation hook (POST to `/admin/archive-season/${seasonNumber}/`)

**File:** `frontend/src/pages/AdminPage.tsx`

- [x] In `ScoringTab`, add an "Archive Season N" button below the scoring controls, styled with a red/destructive tone
- [x] Show a confirmation step before firing: set a `pendingArchive` boolean state; first click shows "Are you sure? This is irreversible." with a confirm button

Test: Admin panel shows correct active season number; Archive button triggers the endpoint and invalidates league queries.

---

## Task 7 — Dashboard: split active vs archived leagues

**File:** `frontend/src/pages/DashboardPage.tsx`

- [x] Update `League` import to include `is_archived` (already available after Task 3)
- [x] Derive `activeLeagues` and `archivedLeagues` from `leagues`
- [x] Render `activeLeagues` as the main grid (unchanged)
- [x] Below the main grid, if `archivedLeagues.length > 0`, render a collapsible "Past Seasons" section (collapsed by default)
- [x] Archived league cards: replace the draft-status badge with a gray "Archived" badge; keep the link functional

Test: Archived leagues appear in "Past Seasons" section, not in main grid; clicking still navigates to the league.

---

## Task 8 — LeaguePage: archived banner + hide action buttons

**File:** `frontend/src/pages/LeaguePage.tsx`

- [x] Read `league?.is_archived`
- [x] Replace Draft + My Roster action buttons with a gray "Archived" span when `is_archived` is true
- [x] Add an info banner below the page header when `is_archived` is true:
  "This league has concluded. All scores and rosters are preserved as a read-only record."

Test: Archived league page shows banner, no Draft/My Roster buttons; tabs (Leaderboard, Chart, Picks) still work.

---

## Task 9 — Update TypeScript `League` interface

**File:** `frontend/src/api/leagues.ts`

- [x] Add `is_archived: boolean` to the `League` interface

---

## Task 10 — Rebuild and redeploy frontend

- [x] `docker compose build frontend && docker compose up -d frontend`

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — Sync fix (is_active bug) | — |
| 2 — League.is_archived model | — |
| 3 — Serializer | 2 |
| 4 — Write guards | 2 |
| 5 — Archive endpoint | 2 |
| 6 — AdminPage dynamic season | 5 |
| 9 — TS League interface | 3 |
| 7 — Dashboard split | 9 |
| 8 — LeaguePage banner | 9 |
| 10 — Build + deploy | 6, 7, 8, 9 |
