# SurvivorPool

A Survivor TV show fantasy game. Players draft 5 castaways at the start of each US season, earn points automatically after every episode airs, and compete in private invite-only leagues with a live leaderboard.

## Features

- **Google OAuth sign-in** — no passwords, one-click authentication
- **Private leagues** — create a league, share an invite code, members join by code
- **Draft system** — pick up to 5 castaways before the draft lock date; draft window can be opened/closed by the league owner
- **Automatic scoring** — Celery Beat syncs episode data nightly and scores any unscored episodes; 40+ event types detected from the survivoR dataset
- **Leaderboard** — per-episode point breakdowns, standings ranked by total score
- **Picks grid** — see all members' castaway selections and pick counts (hidden until draft closes)
- **Swap perk** — each roster gets one free castaway swap before the merge episode
- **Boost perk** — double points for one chosen future episode (non-finale)
- **Activity log** — league owner can see a timeline of draft saves and perk usage
- **Superadmin panel** — manage leagues, rescore episodes, update scoring config, advance seasons, update castaway aliases/photos
- **Email notifications** — Gmail SMTP for transactional emails

## Quick start

```bash
cp .env.example .env     # fill in required variables (see table below)
make up                  # docker compose up -d (builds images on first run)
make migrate             # run Django migrations
make sync SEASON=50      # seed the database with castaways and episodes
```

Access the app at **http://localhost:3000**.  
The Django admin is at **http://localhost:8000/admin/** (only reachable from the host machine since the port is bound to 127.0.0.1).

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key — generate a new one for production |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth 2.0 client ID (backend token verification) |
| `VITE_GOOGLE_CLIENT_ID` | Yes | Same client ID, passed to the Vite build for the frontend button |
| `ALLOWED_HOSTS` | Yes (prod) | Comma-separated hostnames Django will serve (e.g. `yourdomain.com,localhost`) |
| `SUPERADMIN_EMAILS` | Yes | Comma-separated emails granted superadmin access to `/admin` |
| `DATABASE_URL` | No | Defaults to the local PostgreSQL service |
| `REDIS_URL` | No | Defaults to the local Redis service |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated allowed origins (default: `http://localhost:5173,http://localhost:80`) |
| `CSRF_TRUSTED_ORIGINS` | No | Comma-separated origins for CSRF (required behind HTTPS proxy, e.g. `https://yourdomain.com`) |
| `DEBUG` | No | Set to `False` in production |
| `ACTIVE_SEASON` | No | Only needed to bootstrap a fresh database; season is tracked in DB after first sync |
| `EMAIL_HOST_USER` | No | Gmail address for outgoing email |
| `EMAIL_HOST_PASSWORD` | No | Gmail app password (16 characters, not your account password) |
| `ADMIN_SITE_URL` | No | Full URL of the site, used in notification email links (e.g. `https://yourdomain.com`) |

## Adding a new season

1. Run the sync command with the new season number:
   ```bash
   make sync SEASON=51
   ```
   This downloads castaways and episodes from survivoR2py, upserts the database, and sets the draft lock date to Episode 2's air date.

2. Validate event string detectors against the new season's data before it starts:
   ```bash
   make validate-events SEASON=51
   ```
   Review the output and update the relevant detectors in `backend/apps/scoring/event_detector.py` if new string values appear.

3. Update `ACTIVE_SEASON=51` in `.env` and restart the backend.

## Scoring

**Automatic:** Celery Beat scores unscored episodes nightly at 9:05 PM PT after syncing fresh data at 8:00 PM PT.

**Manual — score a specific episode:**
```bash
make score SEASON=51 EPISODE=3
```

**Manual — rescore an already-scored episode** (e.g. after a data correction):
```bash
docker compose exec backend python manage.py score_episode_now 51 3 --force
```

Alternatively, use the **Rescore** action in the superadmin panel or the Django admin Episodes page.

## Adjusting point values

Edit `scoring_config.json` at the project root. Keys are event names; values are integer point totals. Current defaults:

| Event | Pts | Event | Pts |
|---|---|---|---|
| sole_survivor | 50 | find_idol | 20 |
| go_to_rocks | 40 | play_idol | 20 |
| survive_tiebreak | 30 | saved_by_idol | 20 |
| finalist | 30 | 2nd_idol_in_week | 20 |
| quit_or_removed | 30 | find_clue | 15 |
| reenter_game | 30 | gain_advantage | 15 |
| individual_immunity | 25 | play_advantage | 15 |
| win_fire_making | 25 | survive_tribal | 15 |
| give_away_idol | 25 | advance_a_week | 15 |
| idol_received | 25 | deny_advantage | 15 |
| special_idol | 25 | disadvantage | 15 |
| exiled_from_tribe | 20 | make_jury | 10 |
| medical_medevac | 20 | tribe_immunity | 10 |
| steal_extra_vote | 20 | individual_reward | 10 |
| vote_out_with_idol | 15 | group_reward | 5 |
| **eliminated** | **−15** | | |

The file is mounted into the backend container. Restart the backend after changes:
```bash
make down && make up
```

## Running tests

```bash
make test
```

## Project structure

```
├── backend/
│   ├── apps/
│   │   ├── accounts/     # Google OAuth, JWT tokens, user model
│   │   ├── castaways/    # Season, Castaway, Episode models + Fandom image fetcher
│   │   ├── leagues/      # League, Roster, RosterSlot, Perk, leaderboard, draft API
│   │   ├── scoring/      # survivoR data loader, 40+ event detectors, scoring engine, Celery tasks
│   │   └── admin_panel/  # Superadmin-only API: league management, rescoring, season progression
│   └── config/           # Django settings, URL config, Celery config
├── frontend/
│   └── src/
│       ├── api/          # Axios client + TanStack Query hooks
│       ├── components/   # Layout, Breadcrumbs, ProtectedRoute, SuperAdminRoute
│       ├── hooks/        # useAuth (context-based, shared across components)
│       └── pages/        # Login, Dashboard, Draft, Roster, League, Info, Admin
├── infra/                # Terraform for AWS EC2 deployment (see infra/README.md)
├── scoring_config.json   # Event point values — edit to adjust scoring
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Automated scoring schedule

Celery Beat runs two tasks daily (Pacific time):

| Time | Task |
|---|---|
| 8:00 PM PT | `sync_season_data` — fetches fresh castaway and episode data from survivoR2py |
| 9:05 PM PT | `score_active_season` — scores any episodes whose air date has passed and are not yet scored |

Episodes are scored at most once (`Episode.scored_at` prevents double-scoring). Use `make score` or the admin panel to rescore.

## Deployment

Production runs on a single AWS EC2 instance provisioned by Terraform. See [`infra/README.md`](infra/README.md) for setup instructions. The stack sits behind NGINX Proxy Manager (external reverse proxy) which handles TLS termination. The frontend container also acts as an internal reverse proxy, routing `/api/*` requests to the Django backend.

When deploying behind an HTTPS reverse proxy, set:
```
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com
```
