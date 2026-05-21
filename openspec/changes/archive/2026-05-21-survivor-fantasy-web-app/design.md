# Design: Survivor Fantasy Web App

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Django 5 + Django REST Framework + SimpleJWT |
| Auth | Google OAuth 2.0 (ID token verification via `google-auth` library) |
| Task queue | Celery + Redis (broker & result backend) |
| Database | PostgreSQL 16 |
| Frontend | React 18 + Vite + Tailwind CSS + TanStack Query + Recharts |
| Google Sign-In (frontend) | `@react-oauth/google` |
| Data source | survivoR2py GitHub repo (CSV via raw URLs, US seasons only) |
| Deployment | Docker Compose |

---

## Repository Layout

```
SurvivorPool/
├── backend/
│   ├── manage.py
│   ├── config/              # Django project settings, urls, wsgi, celery.py
│   ├── apps/
│   │   ├── accounts/        # User model, Google OAuth endpoint, JWT issuance
│   │   ├── leagues/         # League, Roster, RosterSlot, Perk models + API
│   │   ├── castaways/       # Season, Castaway, Episode models + sync from survivoR2py
│   │   └── scoring/         # event_detector, engine, tasks, PlayerEpisodeScore
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # TanStack Query hooks + axios client
│   │   ├── components/      # Shared UI primitives
│   │   └── pages/           # Login, Dashboard, League, Draft, Leaderboard, Roster
│   ├── index.html
│   └── package.json
├── scoring_config.json      # Point values — single source of truth
├── docker-compose.yml
└── .env.example
```

---

## Authentication

### Flow

1. Frontend renders a **"Sign in with Google"** button (`@react-oauth/google`).
2. User authenticates with Google → frontend receives a Google **ID token** (JWT issued by Google).
3. Frontend `POST /api/v1/auth/google/` with `{ "id_token": "..." }`.
4. Backend verifies the ID token using `google.oauth2.id_token.verify_oauth2_token()` against Google's public keys.
5. Backend extracts `sub` (stable Google user ID), `email`, `name`, `picture` from the verified payload.
6. Backend **find-or-creates** a `User` row keyed on `google_id`.
7. Backend issues its own **SimpleJWT** access + refresh token pair and returns them.
8. Frontend stores the JWT pair in `localStorage`; axios interceptor injects `Authorization: Bearer <access>` on all API calls and uses the refresh token on 401.

### No passwords

The `User` model has no usable password (`set_unusable_password()` on creation). There is no register page, no password reset flow. If a user's Google account is inaccessible, so is their Survivor Pool account.

---

## Data Models

### accounts app

```
User (extends AbstractUser)
  google_id      (varchar, unique — Google's stable "sub" claim)
  email          (unique)
  display_name   (from Google name, editable)
  avatar_url     (Google picture URL)
  username       (set to google_id, satisfies AbstractUser; not exposed in UI)
```

### castaways app

```
Season
  season_number  (int, PK-like; e.g. 50)
  name           (e.g. "Survivor 50: Winners at War II")
  version        (always "US" — only US seasons are synced)
  is_active      (bool — which season the scoring pipeline targets)
  draft_lock_date (date — auto-set to Episode 2 air_date when episodes are synced)

Castaway
  castaway_id    (e.g. "US5001", from survivoR2py)
  season → Season
  name
  age            (nullable)
  hometown       (nullable)
  occupation     (nullable)
  is_eliminated  (bool, updated by sync task)
  eliminated_episode (nullable int)

Episode
  season → Season
  episode_number
  air_date
  scored_at      (nullable datetime — set when scoring task completes for this ep)
```

### leagues app

```
League
  name
  slug           (URL-safe unique identifier, auto-generated from name)
  season → Season
  owner → User
  invite_code    (random 8-char string for joining)
  created_at

Membership
  league → League
  user → User
  joined_at
  unique_together: (league, user)

Roster
  league → League
  user → User
  unique_together: (league, user)

RosterSlot
  roster → Roster
  castaway → Castaway
  slot_number    (1–5)
  added_at       (datetime — set on draft or swap)

Perk
  roster → Roster
  perk_type      (choices: "swap", "boost")
  used           (bool, default False)
  used_at        (nullable datetime)
  boost_target_episode (nullable int — episode number for 2× multiplier)
  swapped_out_castaway → Castaway (nullable FK)
  swapped_in_castaway  → Castaway (nullable FK)
```

**Draft lock rule**: Draft picks (create/update `RosterSlot`) are only permitted while `timezone.now().date() < season.draft_lock_date`. The draft lock date is `Episode[season, episode_number=2].air_date`, stamped onto `Season.draft_lock_date` by the episode sync task.

**Castaway exclusivity**: Enforced in the draft serializer — a castaway may only appear in one `RosterSlot` per league. Validated at the application layer before write; a DB-level unique constraint on `(roster__league, castaway)` via a through-model provides a safety net.

### scoring app

```
ScoringEvent
  castaway → Castaway
  episode → Episode
  event_name     (e.g. "find_idol", "individual_immunity")
  points         (int — value at time of scoring, copied from scoring_config.json)

PlayerEpisodeScore
  roster → Roster
  episode → Episode
  raw_points     (int — sum of ScoringEvent.points for the roster's castaways)
  multiplier     (decimal default 1.0 — 2.0 when boost perk targets this episode)
  final_points   (int — raw_points × multiplier, stored for fast leaderboard queries)
  unique_together: (roster, episode)
```

---

## Scoring Pipeline

### Season / data scope

All data loads and filters are applied to `version == "US"` seasons. The `ACTIVE_SEASON` env var (e.g. `50`) controls which season the pipeline processes.

### Data ingestion (`apps/scoring/data_loader.py`)

- Downloads CSV tables from `https://raw.githubusercontent.com/stiles/survivoR2py/main/data/processed/csv/{table}.csv`
- Tables: `advantage_movement`, `advantage_details`, `vote_history`, `challenge_results`, `castaways`, `boot_mapping`, `episodes`, `jury_votes`, `season_summary`
- Filters all tables to `version == "US"` **and** the active season number before returning
- Caches DataFrames to `/tmp/survivorpool_cache/{table}_US{season}.pkl` with 23-hour TTL; force-refresh via `refresh=True`
- Raises `DataNotReadyError` if a requested episode's data is not yet present (staleness check)

### Event detection (`apps/scoring/event_detector.py`)

One function per scoring category. Each returns `list[tuple[str, int, str]]` = `(castaway_id, episode_number, event_name)`.

**Idols & Advantages — directly trackable**

| Event key | Detection logic |
|---|---|
| `find_idol` | `advantage_movement[event=="Found"]` ∩ `advantage_details[type contains "idol"]` |
| `find_clue` | `advantage_details` where `clue_details` not null, joined to first "Found" movement row |
| `gain_advantage` | `advantage_movement[event in ("Found","Received")]` for non-idol types |
| `gain_2nd_advantage` | castaway with exactly 2 non-idol acquisition events in same episode |
| `gain_3rd_advantage` | castaway with 3+ non-idol acquisition events in same episode |
| `2nd_idol_in_week` | castaway with 2+ idol acquisition events in same episode |
| `play_idol` | `advantage_movement[event=="Played"]` where type is HII |
| `play_advantage` | `advantage_movement[event=="Played"]` for non-idol types |
| `saved_by_idol` | `advantage_movement[event=="Played"]` where `played_for==castaway` and `success==True` |
| `vote_out_with_idol` | idol played successfully (`success==True`) and the target is eliminated same episode |
| `give_away_idol` | `advantage_movement[event=="Received"]` — look at prior `sequence_id` for the giver |
| `idol_received` | `advantage_movement[event=="Received"]` — the recipient castaway |
| `lose_vote` | `vote_history[vote=="None"]` (castaway had no vote this tribal) |
| `steal_extra_vote` | `advantage_movement` joined to `advantage_details` where `advantage_type` in ("Extra Vote", "Steal-a-Vote") |

**Idols & Advantages — approximated**

| Event key | Approximation | Original scoring category |
|---|---|---|
| `deny_advantage` | `advantage_movement[event=="Nullified"]` cross-referenced to the castaway who played the nullifying advantage (complex join — validate event string against live data) | Deny Advantage (15 pts) |
| `disadvantage` | `advantage_movement[event=="Received"]` joined to `advantage_details` where `advantage_type` contains "Disadvantage" (validate type string against live data) | Disadvantage (15 pts) |
| `special_idol` | `advantage_details` where `advantage_type` not in standard set (HII, Extra Vote, Steal-a-Vote, Idol Nullifier, etc.) — requires inspecting actual type values each season | Special Idol (25 pts) |
| `exiled_from_tribe` | `advantage_movement` journey/exile events — present in Season 41+ New Era data; validate event field values against live data | Exiled from Tribe (20 pts) |
| `medical_medevac` | `castaways[result=="Medevac"]` — captures only full medical evacuations; minor medical attention without evacuation is not tracked | Medical Attention (20 pts) |

**Challenges — directly trackable**

| Event key | Detection logic |
|---|---|
| `tribe_immunity` | `challenge_results[challenge_type=="immunity", result=="Win"]` pre-merge tribal challenges |
| `individual_immunity` | `challenge_results[challenge_type=="immunity", result=="Win"]` post-merge or individual challenges |
| `group_reward` | `challenge_results[challenge_type=="reward", result=="Win"]` tribal/group reward |
| `individual_reward` | `challenge_results[challenge_type=="reward", result=="Win"]` individual reward |
| `picked_for_reward` | castaway attended reward but did not win it (was selected by winner) |

**Tribal & Progression — directly trackable**

| Event key | Detection logic |
|---|---|
| `survive_tribal` | castaway attended tribal council and was not voted out that episode |
| `advance_a_week` | castaway still alive at end of episode (via `boot_mapping`) |
| `eliminated` | `castaways[result=="Voted Out"]` |
| `quit_or_removed` | `castaways[result in ("Quit","Removed")]` |
| `make_jury` | `castaways[jury==True]` — fired once when jury flag appears |
| `finalist` | `castaways[finalist==True, winner==False]` |
| `sole_survivor` | `castaways[winner==True]` |
| `win_fire_making` | `vote_history[vote=="Fire"]` — winner of fire-making challenge |
| `survive_tiebreak` | castaway was part of a tie vote revote and survived |
| `go_to_rocks` | `vote_history[vote in ("Black rock","White rock")]` |
| `reenter_game` | castaway appears in `boot_mapping` with a return/reenter event |

### Excluded events (no survivoR2py source)

The following categories from the user's scoring list have no programmatic source in survivoR2py and are **not** included in automated scoring. They would require manual admin entry if desired in the future:

Catch Shark, Join Named Alliance, Make 1st Fire, Black Box Blur, Physical Altercation, Free Chickens, Kiss Tribemate, Tamper Tribe Food, Create/Find/Play Fake Idol, Fake Advantage (non-idol), Give Immunity Necklace, Family Letter, Family Visit, 3rd Party Prize, Win Car, America's Favorite.

### scoring_config.json (complete)

```json
{
  "deny_advantage": 15,
  "disadvantage": 15,
  "find_clue": 15,
  "gain_2nd_advantage": 15,
  "gain_3rd_advantage": 15,
  "gain_advantage": 15,
  "lose_vote": 15,
  "play_advantage": 15,
  "exiled_from_tribe": 20,
  "steal_extra_vote": 20,
  "vote_out_with_idol": 15,
  "2nd_idol_in_week": 20,
  "find_idol": 20,
  "play_idol": 20,
  "saved_by_idol": 20,
  "give_away_idol": 25,
  "idol_received": 25,
  "special_idol": 25,
  "tribe_immunity": 10,
  "individual_immunity": 25,
  "group_reward": 5,
  "individual_reward": 10,
  "picked_for_reward": 10,
  "medical_medevac": 20,
  "eliminated": 0,
  "make_jury": 10,
  "advance_a_week": 15,
  "survive_tribal": 15,
  "win_fire_making": 25,
  "finalist": 30,
  "quit_or_removed": 30,
  "reenter_game": 30,
  "survive_tiebreak": 30,
  "go_to_rocks": 40,
  "sole_survivor": 50
}
```

> **Note on approximated events**: `deny_advantage`, `disadvantage`, `special_idol`, and `exiled_from_tribe` depend on exact `event` and `advantage_type` string values in survivoR2py. Before the first season run, pull the live tables and inspect `advantage_movement.event.value_counts()` and `advantage_details.advantage_type.value_counts()` to validate detection logic.

### Scoring engine (`apps/scoring/engine.py`)

```
score_episode(season_number, episode_number):
  1. Load & filter US data via data_loader
  2. Run all event_detector functions → collect (castaway_id, episode, event_name) rows
  3. Load scoring_config.json → map event_name → points
     (events not in config are logged as warnings and skipped)
  4. Upsert ScoringEvent rows for each detected event
  5. For each Roster in active leagues for this season:
     a. Sum ScoringEvent.points for castaway_ids in the roster's RosterSlots
     b. Check for Boost perk targeting this episode → set multiplier = 2.0
     c. Upsert PlayerEpisodeScore(roster, episode, raw_points, multiplier, final_points)
  6. Stamp Episode.scored_at = now()
```

### Celery tasks (`apps/scoring/tasks.py`)

```
sync_season_data()            # Beat task — runs daily at 20:00 PT
  → downloads castaways + episodes tables (US only)
  → upserts Season, Castaway, Episode rows
  → sets is_eliminated + eliminated_episode on Castaway
  → sets Season.draft_lock_date = Episode[episode_number=2].air_date if not already set

score_active_season()         # Beat task — runs daily at 21:05 PT
  → finds active US Season + unscored Episodes with air_date <= today
  → calls score_episode() for each
```

---

## API Surface

All endpoints under `/api/v1/`. Auth via `Authorization: Bearer <access_token>` header (SimpleJWT).

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/google/` | Exchange Google ID token for app JWT pair |
| POST | `/auth/token/refresh/` | Refresh access token |

### Leagues
| Method | Path | Description |
|---|---|---|
| GET | `/leagues/` | List leagues the authenticated user belongs to |
| POST | `/leagues/` | Create a league (owner = requesting user) |
| GET | `/leagues/{slug}/` | League detail + member list |
| POST | `/leagues/{slug}/join/` | Join via invite code: `{ "invite_code": "..." }` |
| PATCH | `/leagues/{slug}/` | Update league name (owner only) |

### Castaways (read-only)
| Method | Path | Description |
|---|---|---|
| GET | `/seasons/{season_number}/castaways/` | All castaways for a US season (for draft browsing) |
| GET | `/leagues/{slug}/available-castaways/` | Castaways not yet picked in this league |

### Draft
| Method | Path | Description |
|---|---|---|
| GET | `/leagues/{slug}/draft/` | My current picks + draft window status |
| PUT | `/leagues/{slug}/draft/` | Save picks: array of 5 castaway_ids (allowed until draft_lock_date) |

`PUT /draft/` is idempotent — replaces the full roster. Returns 403 after `Season.draft_lock_date`.

### Roster & Perks
| Method | Path | Description |
|---|---|---|
| GET | `/leagues/{slug}/roster/` | My roster slots + perk status |
| GET | `/leagues/{slug}/roster/{user_id}/` | Another league member's roster (read-only) |
| POST | `/leagues/{slug}/roster/swap/` | Use Swap perk: `{ "out_id": ..., "in_id": ... }` |
| POST | `/leagues/{slug}/roster/boost/` | Use Boost perk: `{ "episode_number": ... }` |

### Scores & Leaderboard
| Method | Path | Description |
|---|---|---|
| GET | `/leagues/{slug}/leaderboard/` | All rosters ranked by cumulative `final_points`; includes per-episode breakdown |
| GET | `/leagues/{slug}/scores/` | My `PlayerEpisodeScore` rows with episode metadata |
| GET | `/leagues/{slug}/scores/{episode}/` | All rosters' scores for a single episode |

### Permissions summary

| Action | Who |
|---|---|
| Read leaderboard | Any league member |
| Read another member's roster/picks | Any league member |
| Modify draft picks | Own roster only; before `draft_lock_date` |
| Use Swap / Boost perk | Own roster only; after draft locks |
| Create / edit league | Owner only for edits; any authenticated user for create |
| Join league | Any authenticated user with correct invite code |

---

## Frontend Pages

| Route | Page | Notes |
|---|---|---|
| `/login` | LoginPage | Single "Sign in with Google" button; no email/password form |
| `/` | Dashboard | Cards per league: rank, total points, castaways remaining |
| `/leagues/new` | CreateLeaguePage | Name field; invite code shown after creation |
| `/leagues/:slug` | LeaguePage | Leaderboard table + Recharts cumulative line chart |
| `/leagues/:slug/draft` | DraftPage | Castaway grid with bio info; pick 5; revisions allowed until lock |
| `/leagues/:slug/roster` | RosterPage | My castaways; perk buttons; swap/boost modals |
| `/leagues/:slug/roster/:userId` | RosterViewPage | Read-only view of another member's roster (no edit controls) |

### Draft page detail

- Shows all castaways for the active season with name, age, hometown, occupation.
- Players can select/deselect castaways freely; current selection persists as a draft until they hit Save.
- A countdown timer shows time remaining until `Season.draft_lock_date`.
- After the lock date, the page renders in read-only mode with a "Draft closed" banner.
- If the user hasn't saved exactly 5 picks before the deadline, they are prompted to complete their roster.

### State management
- TanStack Query for all server state.
- JWT access + refresh tokens in `localStorage`.
- Axios interceptor: inject `Authorization` header; on 401, attempt token refresh; on second 401, redirect to `/login`.
- `GoogleOAuthProvider` wraps the app at the root with `VITE_GOOGLE_CLIENT_ID`.

---

## Deployment

### docker-compose.yml services
- `db`: postgres:16
- `redis`: redis:7
- `backend`: Django + gunicorn (port 8000)
- `celery`: same Django image, `celery worker` command
- `celerybeat`: same Django image, `celery beat` command
- `frontend`: nginx serving the Vite build (port 80)

### Environment variables (`.env`)
```
SECRET_KEY=
DATABASE_URL=postgres://...
REDIS_URL=redis://redis:6379/0
GOOGLE_CLIENT_ID=          # OAuth 2.0 Web Client ID from Google Cloud Console
ACTIVE_SEASON=50
ALLOWED_HOSTS=localhost,yourdomain.com
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com
```

---

## Key Design Decisions

1. **Google ID token exchange (not redirect flow)**: The frontend obtains a Google ID token directly via `@react-oauth/google` and POSTs it to the backend. The backend verifies it server-side. This keeps the API stateless and avoids OAuth redirect/callback complexity in a Docker environment.
2. **`Season.draft_lock_date` auto-set from Episode 2**: Rather than requiring a league owner to enter a deadline, the sync task derives the lock date from Episode 2's air date. All leagues for that season share the same lock date.
3. **Draft is a full `PUT` (replace), not incremental**: Simplifies the API — the client always sends the complete 5-castaway selection. Partial saves are kept client-side until the player is ready.
4. **`Episode.scored_at` as idempotency guard**: The scoring task skips episodes already stamped, so it can run daily safely.
5. **`scoring_config.json` is file-based**: Version-controlled, editable without an admin UI, loaded fresh on every scoring run.
6. **Boost perk stores episode number, not a multiplier on ScoringEvent**: Decouples perk decisions from raw event data; re-scoring after a config change doesn't invalidate perk state.
7. **US-only filter applied at data_loader level**: All DataFrames are filtered to `version == "US"` before any downstream logic sees them. No US-check scattered across detectors.
8. **No WebSockets**: Scores change at most once per day; TanStack Query `refetchInterval` is sufficient.
