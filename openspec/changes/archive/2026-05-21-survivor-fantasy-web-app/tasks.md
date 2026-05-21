# Tasks: Survivor Fantasy Web App

## Phase 1 — Project Foundation

### 1.1 Repository & Docker scaffold
- Initialize Django project (`config/`) with PostgreSQL and Redis settings
- Write `docker-compose.yml` with services: `db`, `redis`, `backend`, `celery`, `celerybeat`, `frontend`
- Write `.env.example` with all required variables documented (including `GOOGLE_CLIENT_ID`)
- Add `requirements.txt`: Django 5, DRF, SimpleJWT, `google-auth`, Celery, redis, psycopg2-binary, pandas, requests
- Write `Makefile` with `make up`, `make migrate`, `make shell` targets

### 1.2 Vite + React frontend scaffold
- Initialize Vite project with React + TypeScript inside `frontend/`
- Install: TanStack Query, axios, Tailwind CSS, Recharts, react-router-dom, `@react-oauth/google`
- Configure Tailwind; set up base layout component with nav bar and auth guard
- Set up Vite proxy to `/api` → `http://backend:8000` for development
- Wrap app root with `GoogleOAuthProvider` reading `VITE_GOOGLE_CLIENT_ID`

### 1.3 Google OAuth authentication
**Backend**
- Create `apps/accounts` with custom `User` model: `google_id` (unique), `email` (unique), `display_name`, `avatar_url`; call `set_unusable_password()` on creation
- Implement `POST /api/v1/auth/google/`: accept `{ "id_token": "..." }`, verify with `google.oauth2.id_token.verify_oauth2_token()`, find-or-create `User`, return SimpleJWT access + refresh pair
- Implement `POST /api/v1/auth/token/refresh/`
- Tests: valid token → returns JWTs + creates user on first call; second call with same google_id → returns JWTs without duplicate user; tampered token → 400

**Frontend**
- Write `LoginPage` with a single `GoogleLogin` component from `@react-oauth/google`
- On credential response, `POST /api/v1/auth/google/`; store returned access + refresh tokens in `localStorage`
- Write axios interceptor: inject `Authorization: Bearer` header; on 401 attempt refresh; on second 401 clear tokens and redirect to `/login`
- Write `useAuth` hook: exposes `user`, `isAuthenticated`, `logout`; reads stored tokens; decodes display_name + avatar from JWT or a `/api/v1/auth/me/` endpoint

---

## Phase 2 — Core Data Models

### 2.1 castaways app models & migrations
- Create `apps/castaways`: `Season` (number, name, version, is_active, draft_lock_date), `Castaway` (castaway_id, season, name, age, hometown, occupation, is_eliminated, eliminated_episode), `Episode` (season, episode_number, air_date, scored_at)
- All Season rows must have `version == "US"`; add a model-level `clean()` validation
- Write initial migrations; register in Django admin

### 2.2 leagues app models & migrations
- Create `apps/leagues`: `League` (name, slug, season, owner, invite_code, created_at), `Membership`, `Roster`, `RosterSlot`, `Perk`
- `League.invite_code`: auto-generate 8-char random string on save
- `League.slug`: auto-generate from name (unique)
- DB-level unique constraint on `(roster__league_id, castaway_id)` via a `UniqueConstraint` on `RosterSlot`
- Write initial migrations; register in Django admin

### 2.3 scoring app models & migrations
- Create `apps/scoring`: `ScoringEvent`, `PlayerEpisodeScore`
- Write initial migrations; register in Django admin

### 2.4 Seed data & scoring config
- Write management command `sync_season <season_number>` that runs the castaways + episodes sync for a given US season (same logic as the Celery task; usable from CLI)
- Create `scoring_config.json` at project root with the complete event → point mapping from design.md

---

## Phase 3 — Scoring Pipeline

### 3.1 Data loader (`apps/scoring/data_loader.py`)
- Implement `load_tables(season, refresh=False)` that downloads all required CSVs from survivoR2py raw URLs
- Apply `version == "US"` filter first, then season number filter, on all tables
- Cache DataFrames to `/tmp/survivorpool_cache/{table}_US{season}.pkl` with 23-hour TTL
- Raise `DataNotReadyError(episode)` if requested episode rows are absent
- Write unit tests with mocked HTTP (use `responses` or `unittest.mock`)

### 3.2 Event detector (`apps/scoring/event_detector.py`)
- Implement one function per event key listed in design.md (both directly-trackable and approximated)
- Each returns `list[tuple[str, int, str]]` = `(castaway_id, episode_number, event_name)`
- Implement `detect_all_events(season, episode_number, tables)` that calls all detectors and deduplicates
- **Approximated events** (`deny_advantage`, `disadvantage`, `special_idol`, `exiled_from_tribe`): log a `DEBUG` message with the detected rows so exact string values can be validated against live data on first run
- Write unit tests for: `find_idol`, `individual_immunity`, `survive_tribal`, `advance_a_week`, `eliminated`, `go_to_rocks`, `sole_survivor`

### 3.3 Scoring engine (`apps/scoring/engine.py`)
- Implement `score_episode(season_number, episode_number)`
  1. Load data → run `detect_all_events` → load scoring_config.json
  2. Upsert `ScoringEvent` rows (skip events not in config, emit warning)
  3. For each `Roster` in active US leagues for this season: sum events, apply Boost multiplier, upsert `PlayerEpisodeScore`
  4. Stamp `Episode.scored_at = now()`
- Write integration test: seed a Roster, inject known ScoringEvents, assert `PlayerEpisodeScore.final_points` correct including Boost 2×

### 3.4 Celery tasks and sync (`apps/scoring/tasks.py`)
- Implement `sync_season_data()`:
  - Download `castaways` + `episodes` CSVs (US only)
  - Upsert `Season`, `Castaway`, `Episode` rows
  - Update `Castaway.is_eliminated` + `eliminated_episode`
  - Set `Season.draft_lock_date = Episode[episode_number=2].air_date` (only if Episode 2 exists and lock not already set)
- Implement `score_active_season()`: find active US Season → find unscored Episodes with `air_date <= today` → call `score_episode()` for each
- Configure Celery Beat in `config/celery.py`: `sync_season_data` at 20:00 PT daily, `score_active_season` at 21:05 PT daily
- Write management command `score_episode_now <season> <episode>` for manual re-runs

---

## Phase 4 — REST API

### 4.1 Auth API (verify end-to-end)
- Smoke-test the full Google → JWT flow with Docker running
- Add `GET /api/v1/auth/me/` returning `{ id, email, display_name, avatar_url }`

### 4.2 Leagues API
- Serializers: `LeagueSerializer` (includes `draft_lock_date` from season), `MembershipSerializer`
- Views: list/create leagues, retrieve by slug, update name (owner only), join via invite code
- Permissions class: `IsLeagueMember` for read; `IsLeagueOwner` for write
- Tests: create, join, duplicate join rejected, non-member can't read, non-owner can't update

### 4.3 Castaways API
- `GET /api/v1/seasons/{season_number}/castaways/` — all castaways for a US season; includes `is_eliminated`
- `GET /api/v1/leagues/{slug}/available-castaways/` — filter out castaway_ids already in any RosterSlot for this league
- Tests: eliminated castaways still returned (players need to see who was picked), picked castaways excluded from available list

### 4.4 Draft API
- `GET /api/v1/leagues/{slug}/draft/` — my current picks + `{ "draft_open": bool, "lock_date": "..." }`
- `PUT /api/v1/leagues/{slug}/draft/` — accept `{ "castaway_ids": [...5 ids...] }`; validate: exactly 5, each available in league, each castaway belongs to the league's season; create/replace `Roster` + `RosterSlot` rows; return 403 with explanation if after `draft_lock_date`
- Tests: initial draft, pick revision before lock, rejected after lock, duplicate castaway within submission rejected, castaway from wrong season rejected

### 4.5 Roster & Perks API
- `GET /api/v1/leagues/{slug}/roster/` — my slots + `[{ "perk_type", "used", "boost_target_episode", "swapped_out", "swapped_in" }]`
- `GET /api/v1/leagues/{slug}/roster/{user_id}/` — read-only view of another member's roster; accessible to any league member
- `POST /api/v1/leagues/{slug}/roster/swap/` — validate: Swap perk unused + draft locked + in_castaway available + season in progress; execute swap; mark perk used
- `POST /api/v1/leagues/{slug}/roster/boost/` — validate: Boost perk unused + target episode not yet scored; mark perk used
- Tests: swap happy path, swap before draft lock rejected, swap after perk used rejected, boost on scored episode rejected, cross-user read succeeds, cross-user write rejected (403)

### 4.6 Scores & Leaderboard API
- `GET /api/v1/leagues/{slug}/leaderboard/` — all rosters with cumulative `final_points` ranked; each entry includes `episodes: [{episode_number, raw_points, multiplier, final_points}]`
- `GET /api/v1/leagues/{slug}/scores/` — my `PlayerEpisodeScore` rows + castaway event breakdown
- `GET /api/v1/leagues/{slug}/scores/{episode}/` — all rosters' scores for one episode (read for all league members)
- Tests: ranking order correct; Boost multiplier reflected; non-member blocked

---

## Phase 5 — Frontend Pages

### 5.1 Auth & routing
- `ProtectedRoute` component: redirects to `/login` if not authenticated
- `LoginPage`: `GoogleLogin` button centered on page; on success call backend `/auth/google/`, store tokens, redirect to `/`
- Nav bar: show `display_name` + avatar; Logout button clears localStorage + redirects

### 5.2 Dashboard
- `DashboardPage`: league cards — league name, user's current rank, total points, eliminated castaways count
- "Create League" button → `CreateLeaguePage` (name field; season auto-set to active season; show invite code on success)
- "Join League" button → modal with invite code input

### 5.3 Draft page
- `DraftPage`: castaway grid — name, age, hometown, occupation; filter/sort controls
- Multi-select up to 5; real-time "X / 5 selected" counter
- Save button calls `PUT /draft/`; debounced auto-save every 10 seconds while the window is open
- Countdown timer to `draft_lock_date`; after lock shows read-only "Draft closed" banner
- If user has no picks, prompt them to draft before the season starts

### 5.4 League / Leaderboard page
- `LeaguePage`: tabs for "Leaderboard" and "Episode Scores"
- Leaderboard tab: sortable table — rank, player avatar + name, per-episode scores (sparkline), cumulative total
- Episode Scores tab: Recharts line chart with one line per player, x-axis = episode, y-axis = cumulative points
- Invite code shown to league owner (copyable)

### 5.5 Roster page
- `RosterPage`: my 5 castaways with elimination status badges; points each castaway has earned
- Swap perk section: if unused, show button → modal (select replacement from available list, confirm); if used, show who was swapped and when
- Boost perk section: if unused, show button → modal (select an unscored future episode, confirm); if used, show which episode was boosted
- Expandable per-castaway event log: list of `ScoringEvent` rows with event name and points

### 5.6 Roster view page (read-only)
- `RosterViewPage` at `/leagues/:slug/roster/:userId`: same layout as `RosterPage` but no edit controls
- Accessible to any league member; shows the target player's display_name and avatar at top

---

## Phase 6 — Hardening & Polish

### 6.1 Error handling & UX polish ✓
- [x] Tailwind `@layer components` utilities: `btn-primary`, `btn-secondary`, `card`, `input`, `label`, `badge-green`, `badge-gray` added to `frontend/src/index.css`

### 6.2 Staleness indicator ✓
- [x] `LeaderboardView` returns `{ entries: [...], last_scored_at: "..." }` — most recent `Episode.scored_at` across the season
- [x] `LeaguePage` displays "Last updated N hours ago" footer; shows yellow warning banner if no scoring in 8+ days

### 6.3 Admin tooling ✓
- [x] `EpisodeAdmin` with "Re-score episode" action (`score_episode` inline per selected episodes)
- [x] `SeasonAdmin` with "Force sync season data" action (queues Celery task)
- [x] `ScoringEventAdmin` and `PlayerEpisodeScoreAdmin` with read-only fields

### 6.4 Security hardening ✓
- [x] `GoogleAuthThrottle` (10/min) on `POST /auth/google/`
- [x] `CORS_ALLOWED_ORIGINS` read from env var
- [x] `scoring_config.json` mounted read-only in `docker-compose.yml`
- [x] `invite_code` only in `LeagueDetailSerializer`, not `LeagueSerializer` (list endpoint)

### 6.5 Data validation script ✓
- [x] `validate_event_strings` management command already implemented in Phase 3

### 6.6 CI & README ✓
- [x] `.github/workflows/ci.yml` — Django tests + TypeScript check on push/PR to main
- [x] `README.md` — Docker setup, adding a season, manual scoring, point value config, event string validation

---

## Implementation Order Summary

| Phase | Depends on |
|---|---|
| 1 — Foundation | — |
| 2 — Data Models | Phase 1 |
| 3 — Scoring Pipeline | Phase 2 |
| 4 — REST API | Phase 2; score endpoints need Phase 3 |
| 5 — Frontend Pages | Phase 4 |
| 6 — Hardening | Phase 5 |
