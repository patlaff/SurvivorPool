# Tasks: Superadmin Panel

## Phase 1 — Backend foundation

### 1.1 Settings + custom JWT token
- [x] Add `SUPERADMIN_EMAILS = env.list('SUPERADMIN_EMAILS', default=['patlaff728@gmail.com'])` to `config/settings.py`
- [x] Create `apps/accounts/tokens.py` with `SurvivorPoolRefreshToken(RefreshToken)` that adds `email`, `display_name`, `avatar_url`, and `is_superadmin` claims to the access token
- [x] In `apps/accounts/views.py` `GoogleLoginView`, replace `RefreshToken.for_user(user)` with `SurvivorPoolRefreshToken.for_user(user)`

### 1.2 League.is_test model + migration
- [x] Add `is_test = models.BooleanField(default=False, ...)` to `League` in `apps/leagues/models.py`
- [x] Write migration `apps/leagues/migrations/0003_league_is_test.py`
- [x] Add `is_test` to `LeagueSerializer` and `LeagueDetailSerializer` fields

### 1.3 Restriction bypasses for test leagues
- [x] `DraftView.put` in `apps/leagues/views.py`: wrap the `is_draft_open` guard with `if not league.is_test:`
- [x] `DraftView.put`: wrap the `already_taken` check with `if not league.is_test:`
- [x] `AvailableCastawaysView.get`: if `league.is_test`, return all season castaways (skip the `exclude(id__in=picked_ids)` filter)
- [x] `SwapPerkView.post`: wrap the `is_draft_open` guard and the merge-window guard with `if not league.is_test:`
- [x] `BoostPerkView.post`: wrap the `air_date` and `scored_at` guards with `if not league.is_test:`

### 1.4 New `apps/admin_panel` app
- [x] Create `apps/admin_panel/` with `__init__.py`, `apps.py`, `permissions.py`, `views.py`, `urls.py`
- [x] `permissions.py`: `IsSuperAdmin` permission — checks `request.user.email in settings.SUPERADMIN_EMAILS`
- [x] Register `'apps.admin_panel'` in `INSTALLED_APPS` in `config/settings.py`
- [x] Wire `path('admin/', include('apps.admin_panel.urls'))` into `config/urls.py` under the `/api/v1/` prefix

### 1.5 Admin league endpoints
- [x] `GET /api/v1/admin/leagues/` — all leagues ordered by `created_at` desc; returns `id, name, slug, owner(display_name, email), member_count, is_test, invite_code, draft_open, created_at`
- [x] `POST /api/v1/admin/leagues/` — create a test league; body `{ "name": "..." }`; uses active US season; sets `is_test=True`; creates Membership for the requesting user; returns league detail

### 1.6 Scoring summary endpoint
- [x] `GET /api/v1/admin/seasons/{season_number}/scoring-summary/` — returns all `ScoringEvent` rows for the season grouped by episode, plus per-castaway totals sorted by total points descending

### 1.7 Scoring config endpoints
- [x] `GET /api/v1/admin/scoring-config/` — reads `scoring_config.json` via `_load_config()` from `apps/scoring/engine.py`; returns `{ "config": {...} }`
- [x] `PUT /api/v1/admin/scoring-config/` — validates all values are non-negative integers; writes atomically (temp file + rename); returns saved config
- [x] `POST /api/v1/admin/rescore/{season_number}/` — re-scores all previously-scored episodes for the season: updates `ScoringEvent.points` from new config, then recalculates `PlayerEpisodeScore` for each roster (preserving Boost multiplier); returns `{ "episodes_rescored": N, "rosters_updated": M }`

---

## Phase 2 — Frontend

### 2.1 Auth: `is_superadmin` + fix page-reload bug
- [x] Add `is_superadmin: boolean` to `AuthUser` interface in `hooks/useAuth.ts`
- [x] Update `decodeUser` to read `email`, `display_name`, `avatar_url`, and `is_superadmin` from JWT payload (fixing existing page-reload empty-string bug)

### 2.2 `SuperAdminRoute` component + routing
- [x] Create `components/SuperAdminRoute.tsx`: wraps children in `<ProtectedRoute>` logic plus a check for `user.is_superadmin`; redirects to `/` if not superadmin
- [x] Add `<Route path="/admin" element={<SuperAdminRoute><AdminPage /></SuperAdminRoute>} />` to `App.tsx`
- [x] Add "Admin" nav link in `Layout.tsx` visible only when `user.is_superadmin`

### 2.3 Admin API hooks (`api/admin.ts`)
- [x] `useAdminLeagues()` — `GET /admin/leagues/`
- [x] `useCreateTestLeague()` — mutation: `POST /admin/leagues/` with `{ name }`
- [x] `useScoringConfig()` — `GET /admin/scoring-config/`
- [x] `useSaveConfig()` — mutation: `PUT /admin/scoring-config/` with `{ config }`
- [x] `useRescoreSeason()` — mutation: `POST /admin/rescore/{season_number}/`
- [x] `useScoringsSummary(seasonNumber)` — `GET /admin/seasons/{seasonNumber}/scoring-summary/`

### 2.4 `AdminPage.tsx` — Leagues tab
- [x] Table of all leagues: Name (link), Owner email, Members, Draft status badge, Test badge (orange "TEST" pill), Created date
- [x] Create Test League form: name input + "Create Test League" button; on success show invite code + link to new league

### 2.5 `AdminPage.tsx` — Scoring Summary tab
- [x] Per-episode accordion: header shows episode number, air date, scored_at, total points; body shows castaway → event → points table
- [x] Castaway totals section: sorted table with eliminated badge

### 2.6 `AdminPage.tsx` — Scoring Config tab
- [x] Editable table: one row per event; event name (read-only monospace) | point value (number input, min 0)
- [x] "Save Config" button with pending state; shows success/error feedback
- [x] "Re-score Season" button; shows `episodes_rescored` and `rosters_updated` on success

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1.1 Settings + JWT | — |
| 1.2 Model + migration | — |
| 1.3 Restriction bypasses | 1.2 |
| 1.4 admin_panel app scaffold | — |
| 1.5 League endpoints | 1.2, 1.4 |
| 1.6 Scoring summary | 1.4 |
| 1.7 Config endpoints | 1.4 |
| 2.1 Auth fixes | 1.1 |
| 2.2 Route + nav | 2.1 |
| 2.3 API hooks | 1.5, 1.6, 1.7 |
| 2.4 Leagues tab | 2.3 |
| 2.5 Scoring Summary tab | 2.3 |
| 2.6 Config tab | 2.3 |
