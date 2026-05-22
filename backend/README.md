# Backend

Django REST API for SurvivorPool — handles authentication, league management, castaway data synchronization, and automated episode scoring.

## Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| Django | 5.0 | Web framework |
| Django REST Framework | 3.15 | API serialization and views |
| djangorestframework-simplejwt | 5.3 | JWT authentication |
| google-auth | 2.28 | Google OAuth 2.0 token verification |
| Celery | 5.3 | Async task queue and scheduler |
| Redis | 7 | Celery broker and result backend |
| PostgreSQL | 16 | Primary database |
| psycopg2-binary | 2.9 | PostgreSQL driver |
| pandas | 2.2 | Data manipulation for survivoR CSV ingestion |
| gunicorn | 21.2 | WSGI server |
| django-cors-headers | 4.3 | CORS for frontend dev |
| dj-database-url | 2.1 | Database URL parsing |

## Project Structure

```
backend/
├── config/
│   ├── settings.py        # Django settings (auth, database, CORS, installed apps)
│   ├── urls.py            # Root URL conf — mounts all app routers under /api/v1/
│   └── celery.py          # Celery app and Beat schedule (sync at 8 PM PT, score at 9:05 PM PT)
├── apps/
│   ├── accounts/          # Custom user model, Google OAuth login, /me endpoint
│   ├── castaways/         # Season, Castaway, Episode models and read endpoints
│   ├── leagues/           # League CRUD, draft, roster, perks, leaderboard, activity
│   ├── scoring/           # Event detection, scoring engine, Celery tasks
│   └── admin_panel/       # Superadmin endpoints (leagues, config, rescore)
├── requirements.txt
└── manage.py
```

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16
- Redis 7
- (Optional) Docker — see root `docker-compose.yml` for the full stack

### Install Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

The backend reads all configuration from environment variables (or a `.env` file at the repo root when running via Docker Compose). See `.env.example` in the repo root for a template.

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | `True` for development (default `False`) |
| `DATABASE_URL` | Yes | PostgreSQL connection string, e.g. `postgres://user:pass@localhost:5432/survivorpool` |
| `REDIS_URL` | Yes | Redis connection string, e.g. `redis://localhost:6379/0` |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth 2.0 client ID for token verification |
| `CORS_ALLOWED_ORIGINS` | Yes | Comma-separated list of allowed frontend origins |
| `ACTIVE_SEASON` | Yes | Season number to treat as the active season (integer) |

### Run Migrations

```bash
python manage.py migrate
```

### Create a Superuser

```bash
python manage.py createsuperuser
```

The superuser flag (`is_superadmin`) is stored on the `User` model and included as a JWT claim. Use the Django admin (`/admin/`) to set it on accounts that need access to the admin panel.

### Start the Development Server

```bash
python manage.py runserver
```

API is available at `http://localhost:8000/api/v1/`.

### Start Celery Worker

In a separate terminal:

```bash
celery -A config worker -l info
```

### Start Celery Beat Scheduler

In a separate terminal:

```bash
celery -A config beat -l info
```

Beat runs two scheduled tasks daily (Pacific time):
- **8:00 PM** — Sync season data from survivoR
- **9:05 PM** — Score any unscored episodes from today or earlier

---

## Apps

### `accounts`

Custom user model and Google OAuth login.

#### Models

**`User`** (extends `AbstractUser`)

| Field | Type | Notes |
|-------|------|-------|
| `email` | EmailField (unique) | Used as `USERNAME_FIELD` |
| `google_id` | CharField (unique) | Google sub claim |
| `display_name` | CharField | From Google profile |
| `avatar_url` | URLField | Google profile picture |
| `is_superadmin` | BooleanField | Grants access to admin panel |

#### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/google/` | None | Exchange Google `id_token` for JWT access + refresh tokens |
| GET | `/api/v1/auth/me/` | JWT | Return current user profile |
| POST | `/api/v1/auth/token/refresh/` | None | Refresh access token using refresh token |

#### Login Flow

1. Frontend sends `{ id_token: "..." }` from Google OAuth dialog
2. Backend verifies the token with Google using `google.oauth2.id_token.verify_oauth2_token`
3. User is created or updated (display_name and avatar_url sync on every login)
4. Access + refresh JWTs are returned; `is_superadmin` is embedded as a JWT claim

---

### `castaways`

Season and castaway data, synchronized nightly from the [survivoR R package](https://github.com/doehm/survivoR).

#### Models

**`Season`**

| Field | Type | Notes |
|-------|------|-------|
| `season_number` | IntegerField (unique) | |
| `name` | CharField | e.g. "Survivor: Borneo" |
| `version` | CharField | Always `"US"` |
| `is_active` | BooleanField | Only one season is active at a time |
| `draft_lock_date` | DateTimeField | Set to Episode 2 air date during sync |

**`Castaway`**

| Field | Type | Notes |
|-------|------|-------|
| `castaway_id` | CharField (unique) | Composite key from survivoR |
| `season` | FK → Season | |
| `name` | CharField | |
| `age` | IntegerField | |
| `hometown` | CharField | |
| `occupation` | CharField | |
| `is_eliminated` | BooleanField | Updated each sync |
| `eliminated_episode` | IntegerField (nullable) | Episode number of elimination |

**`Episode`**

| Field | Type | Notes |
|-------|------|-------|
| `season` | FK → Season | |
| `episode_number` | IntegerField | |
| `air_date` | DateField | |
| `scored_at` | DateTimeField (nullable) | Null until scoring engine runs |
| `is_merge` | BooleanField | |
| `is_finale` | BooleanField | |

#### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/active-season/` | None | Active season with episode list |
| GET | `/api/v1/seasons/:n/castaways/` | None | All castaways for a season |
| GET | `/api/v1/seasons/:n/episodes/` | None | All episodes for a season |

---

### `leagues`

Core gameplay: league management, drafting, perks, leaderboard, and activity feed.

#### Models

**`League`**

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField | |
| `slug` | CharField (unique) | URL-safe identifier |
| `season` | FK → Season | Set to active season on creation |
| `owner` | FK → User | |
| `invite_code` | CharField (unique) | 8-character uppercase alphanumeric |
| `draft_close_at` | DateTimeField (nullable) | Per-league override for draft deadline |
| `draft_force_open` | BooleanField | Owner can force-open draft regardless of date |
| `is_test` | BooleanField | Test leagues bypass draft date restrictions |

**`Membership`**

Junction of `(league, user)` — unique together.

**`Roster`**

One per `(league, user)` pair — unique together. The container for a player's picks and perks.

**`RosterSlot`**

| Field | Type | Notes |
|-------|------|-------|
| `roster` | FK → Roster | |
| `slot_number` | IntegerField | 1–5, unique per roster |
| `castaway` | FK → Castaway | unique per roster (no duplicate picks) |
| `added_at` | DateTimeField | |

**`DraftSave`**

Audit log of every draft save action.

| Field | Type | Notes |
|-------|------|-------|
| `roster` | FK → Roster | |
| `castaway_names` | JSONField | Snapshot of pick names at save time |
| `saved_at` | DateTimeField | |

**`Perk`**

| Field | Type | Notes |
|-------|------|-------|
| `roster` | FK → Roster | |
| `perk_type` | CharField | `"swap"` or `"boost"` |
| `used_at` | DateTimeField (nullable) | Null until perk is used |
| `swap_out` | FK → Castaway (nullable) | Swap: the castaway being replaced |
| `swap_in` | FK → Castaway (nullable) | Swap: the new castaway |
| `boost_target_episode` | IntegerField (nullable) | Boost: the episode getting 2x |

#### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/leagues/` | JWT | List user's leagues |
| POST | `/api/v1/leagues/` | JWT | Create a new league |
| POST | `/api/v1/leagues/join/` | JWT | Join a league by invite code |
| GET | `/api/v1/leagues/:slug/` | Member | League detail with member list |
| PATCH | `/api/v1/leagues/:slug/` | Owner | Update league name |
| POST | `/api/v1/leagues/:slug/join/` | JWT | Join by slug (with code in body) |
| GET | `/api/v1/leagues/:slug/available-castaways/` | Member | All pickable castaways |
| GET | `/api/v1/leagues/:slug/draft/` | Member | Draft open status and current picks |
| PUT | `/api/v1/leagues/:slug/draft/` | Member | Save draft picks (list of castaway IDs) |
| PATCH | `/api/v1/leagues/:slug/draft-window/` | Owner | Override `draft_close_at` / `draft_force_open` |
| GET | `/api/v1/leagues/:slug/roster/` | Member | Current user's roster with scores |
| GET | `/api/v1/leagues/:slug/roster/:userId/` | Member | Another member's roster |
| POST | `/api/v1/leagues/:slug/roster/swap/` | Member | Use swap perk |
| POST | `/api/v1/leagues/:slug/roster/boost/` | Member | Use boost perk |
| GET | `/api/v1/leagues/:slug/leaderboard/` | Member | Ranked scores with episode breakdown |
| GET | `/api/v1/leagues/:slug/scores/` | Member | Requesting user's episode score breakdown |
| GET | `/api/v1/leagues/:slug/activity/` | Member | Timeline of draft/perk events |

#### Draft Open Logic

`utils.is_draft_open(league)` returns `True` if either:
- `league.draft_force_open` is `True`, **or**
- Today is before the season's `draft_lock_date` (Episode 2 air date)

A per-league `draft_close_at` override takes precedence over the season default when set.

#### Draft Privacy

During the open draft window, the leaderboard and roster views hide other members' castaway names. After the draft closes, all picks are fully visible. This prevents copying and encourages independent strategy.

#### Perks

Each roster receives one **swap** and one **boost** perk automatically when the first draft save is submitted.

- **Swap**: Replaces one castaway in the roster with any other. Available until the draft window closes.
- **Boost**: Applies a 2× points multiplier to all castaway scores for one chosen episode. The episode must not have aired yet when the boost is applied.

#### Permissions

| Class | Description |
|-------|-------------|
| `IsLeagueMember` | User must have a `Membership` row for the league |
| `IsLeagueOwner` | User must be `league.owner` |
| `IsSuperAdmin` | User must have `is_superadmin=True` on their profile |

---

### `scoring`

Automated scoring pipeline: data ingestion, event detection, and point calculation.

#### Models

**`ScoringEvent`** — unique on `(castaway, episode, event_name)`

| Field | Type | Notes |
|-------|------|-------|
| `castaway` | FK → Castaway | |
| `episode` | FK → Episode | |
| `event_name` | CharField | Matches a key in `scoring_config.json` |
| `points` | IntegerField | Snapshot of point value at scoring time |

**`PlayerEpisodeScore`** — unique on `(roster, episode)`

| Field | Type | Notes |
|-------|------|-------|
| `roster` | FK → Roster | |
| `episode` | FK → Episode | |
| `raw_points` | IntegerField | Sum of `ScoringEvent.points` for roster's castaways |
| `multiplier` | FloatField | `1.0` normally, `2.0` if boost active |
| `final_points` | IntegerField | `raw_points × multiplier` |

#### Modules

**`data_loader.py`**

Downloads survivoR JSON exports from GitHub and returns pandas DataFrames. Loads:
- `castaways` — castaway demographics
- `episodes` — air dates, merge/finale flags
- `advantage_movement` — idol finds, plays, transfers
- `advantage_details` — idol types
- `tribe_mapping` — which tribe a castaway was on per episode
- `vote_history` — tribal council vote records

Validates that episode data exists and is complete before scoring begins.

**`event_detector.py`**

Pattern-matches raw survivoR event strings into named scoring categories. Each function receives a castaway ID and episode number and returns a list of detected event names.

Detectable events and their default point values (configurable via `scoring_config.json`):

| Category | Event | Default Pts |
|----------|-------|-------------|
| Idols | `find_idol` | +10 |
| | `play_idol` | +5 |
| | `saved_by_idol` | +10 |
| | `give_away_idol` | +5 |
| | `idol_received` | +5 |
| | `special_idol` | +10 |
| Advantages | `find_clue` | +3 |
| | `gain_advantage` | +5 |
| | `gain_2nd_advantage` | +5 |
| | `gain_3rd_advantage` | +5 |
| Immunity | `tribe_immunity` | +5 |
| | `individual_immunity` | +10 |
| | `win_fire_making` | +10 |
| Rewards | `group_reward` | +3 |
| | `individual_reward` | +5 |
| | `picked_for_reward` | +3 |
| Tribal | `survive_tribal` | +2 |
| | `lose_vote` | -5 |
| | `vote_out_with_idol` | +10 |
| | `eliminate` | -15 |
| Medical | `medical_medevac` | -15 |
| Advancement | `go_to_rocks` | +5 |
| | `survive_tiebreak` | +5 |
| | `make_jury` | +10 |
| | `advance_a_week` | +2 |
| | `reenter_game` | +10 |
| Finals | `finalist` | +15 |
| | `sole_survivor` | +25 |
| | `quit_or_removed` | -10 |
| Disadvantages | `deny_advantage` | +5 |
| | `disadvantage` | -5 |
| | `exiled_from_tribe` | -3 |
| | `steal_extra_vote` | +5 |

**`engine.py`**

Orchestrates the full scoring run for a single episode:

1. Loads `scoring_config.json` for current point values
2. Calls `event_detector` for every castaway active in the episode
3. Upserts `ScoringEvent` rows (idempotent — safe to re-run)
4. For each `Roster` in the season's leagues:
   - Sums `ScoringEvent.points` for the roster's 5 castaways
   - Checks if the roster has an active boost perk targeting this episode
   - Writes `PlayerEpisodeScore` with `raw_points`, `multiplier`, and `final_points`
5. Stamps `Episode.scored_at` to prevent re-scoring

**`tasks.py`**

Celery tasks scheduled by Beat:

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_season_data` | Daily 8:00 PM PT | Fetches latest castaway/episode data from survivoR, upserts DB records, sets `draft_lock_date` to Episode 2 air date |
| `score_active_season` | Daily 9:05 PM PT | Finds all episodes where `air_date ≤ today` and `scored_at` is null, then scores each |

---

### `admin_panel`

Superadmin-only endpoints for league management, scoring configuration, and manual scoring triggers.

All views require the `IsSuperAdmin` permission.

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/leagues/` | List all leagues (test and production) |
| POST | `/api/v1/admin/leagues/` | Create a test league (bypasses draft restrictions) |
| GET | `/api/v1/admin/scoring-config/` | Load current `scoring_config.json` as JSON |
| PUT | `/api/v1/admin/scoring-config/` | Save `scoring_config.json` (takes effect on next scoring run) |
| GET | `/api/v1/admin/seasons/:n/scoring-summary/` | Events detected and castaway totals for a season |
| POST | `/api/v1/admin/rescore/:n/` | Delete and recalculate all `PlayerEpisodeScore` rows for a season |
| POST | `/api/v1/admin/score-unscored/:n/` | Score all past unscored episodes for a season |

---

## Scoring Configuration

Point values are stored in `scoring_config.json` at the repo root. This file is bind-mounted into the backend container at runtime and read by the scoring engine on each run. Editing the file via the admin API takes effect on the next scheduled scoring run (or immediately after a manual rescore).

Example structure:

```json
{
  "find_idol": 10,
  "play_idol": 5,
  "saved_by_idol": 10,
  "individual_immunity": 10,
  "eliminate": -15,
  "sole_survivor": 25
}
```

To change point values mid-season, edit the config via the admin panel and trigger a full rescore. All `PlayerEpisodeScore` rows for the season are recalculated using the new values.

---

## Celery Beat Schedule

Defined in `config/celery.py`:

```python
app.conf.beat_schedule = {
    "sync-season-data": {
        "task": "apps.scoring.tasks.sync_season_data",
        "schedule": crontab(hour=20, minute=0, day_of_week="*"),  # 8 PM UTC-8 (PT)
    },
    "score-active-season": {
        "task": "apps.scoring.tasks.score_active_season",
        "schedule": crontab(hour=21, minute=5, day_of_week="*"),  # 9:05 PM PT
    },
}
```

Both tasks use the `ACTIVE_SEASON` environment variable to target the correct season. The 65-minute gap between sync and scoring ensures fresh data is in the database before scoring begins.

---

## API Authentication

All non-public endpoints require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens expire after 5 minutes. The frontend automatically refreshes them using the refresh token (7-day TTL). Token endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/google/` | Exchange Google id_token for JWT pair |
| POST | `/api/v1/auth/token/refresh/` | Exchange refresh token for new access token |

---

## Running Tests

```bash
python manage.py test
```

---

## Production Deployment

In production the backend runs as a Gunicorn WSGI server inside Docker:

```
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

Migrations and static file collection run automatically at container startup. See the root `docker-compose.yml` and `../infra/README.md` for the full deployment setup.
