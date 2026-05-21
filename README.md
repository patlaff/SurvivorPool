# SurvivorPool

A Survivor TV show fantasy game. Players draft 5 castaways at the start of each US season, earn points automatically after every episode, and compete in private leagues with a live leaderboard.

## Quick start

```bash
cp .env.example .env          # fill in GOOGLE_CLIENT_ID and SECRET_KEY
make up                       # docker compose up --build -d
make migrate                  # run Django migrations
make createsuperuser          # optional: create an admin account
```

The frontend is at **http://localhost:3000** and the Django admin at **http://localhost:8000/admin/**.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key (generate a new one for production) |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth 2.0 client ID |
| `DATABASE_URL` | No | Defaults to local PostgreSQL service |
| `REDIS_URL` | No | Defaults to local Redis service |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated frontend origins (default: localhost:5173,localhost:3000) |
| `ACTIVE_SEASON` | No | US season number to score (default: 50) |
| `DEBUG` | No | Set to `False` in production |

## Adding a new season

1. Update `ACTIVE_SEASON` in `.env` to the new season number.
2. Trigger a manual sync:
   ```bash
   make sync SEASON=51
   ```
   This downloads castaways and episodes from survivoR2py, upserts the database, and sets the draft lock date to Episode 2's air date.
3. Run the event string validator before the season starts to make sure approximated event detectors match live data:
   ```bash
   make validate-events SEASON=51
   ```

## Scoring manually

To score a specific episode outside the nightly schedule:

```bash
make score SEASON=51 EPISODE=3
```

To re-score an already-scored episode (e.g. after a data correction):

```bash
make score SEASON=51 EPISODE=3
```

Alternatively, use the Django admin "Re-score episode" action on the Episodes page.

## Adjusting point values

Edit `scoring_config.json` at the project root. Keys are event names; values are integer point totals. The file is mounted read-only into the backend container — restart the backend after changes:

```bash
make down && make up
```

## Validating event strings before a new season

The scoring pipeline approximates some events (e.g. `deny_advantage`, `exiled_from_tribe`) by pattern-matching strings in the survivoR2py CSVs. These strings can change between seasons. Run the validator to print the raw value counts:

```bash
make validate-events SEASON=51
```

Review the output and update the relevant detector functions in `backend/apps/scoring/event_detector.py` if new string values appear.

## Running tests

```bash
make test
```

## Project structure

```
├── backend/
│   ├── apps/
│   │   ├── accounts/     # Google OAuth, user model
│   │   ├── castaways/    # Season, Castaway, Episode models
│   │   ├── leagues/      # League, Roster, Perk, leaderboard API
│   │   └── scoring/      # Data loader, event detector, engine, Celery tasks
│   └── config/           # Django settings, URLs, Celery config
├── frontend/
│   └── src/
│       ├── api/          # TanStack Query hooks
│       ├── components/   # Layout, ProtectedRoute
│       ├── hooks/        # useAuth
│       └── pages/        # LoginPage, DashboardPage, DraftPage, etc.
├── scoring_config.json   # Point values per event (edit to adjust scoring)
├── docker-compose.yml
└── Makefile
```

## Automated scoring schedule

Celery Beat runs two tasks daily (Pacific time):

| Time | Task |
|---|---|
| 8:00 PM PT | `sync_season_data` — downloads fresh castaways + episodes from survivoR2py |
| 9:05 PM PT | `score_active_season` — scores any unscored episodes whose air date has passed |

Episodes are scored at most once (`Episode.scored_at` timestamp prevents double-scoring). To re-score, use the Django admin action or `make score`.
