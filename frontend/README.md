# Frontend

React + TypeScript single-page application for SurvivorPool — a Survivor TV show fantasy game where players draft castaways, earn points automatically after each episode, and compete in private leagues.

## Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| React | 18.2 | UI framework |
| TypeScript | 5.2 | Type safety |
| Vite | 5.1 | Build tool and dev server |
| Tailwind CSS | 3.4 | Utility-first styling |
| TanStack Query | 5.28 | Data fetching, caching, mutations |
| React Router | 6.22 | Client-side routing |
| Axios | 1.6 | HTTP client with JWT interceptors |
| `@react-oauth/google` | 0.12 | Google OAuth 2.0 login |
| Recharts | 2.12 | Leaderboard score charts |

## Project Structure

```
frontend/
├── public/                    # Static assets
├── src/
│   ├── api/
│   │   ├── client.ts          # Axios instance with JWT refresh interceptors
│   │   ├── leagues.ts         # TanStack Query hooks for leagues, drafts, rosters, scores
│   │   ├── admin.ts           # Admin API hooks (test leagues, rescore, scoring config)
│   │   └── info.ts            # Public API hooks (active season, scoring config)
│   ├── components/
│   │   ├── Layout.tsx         # Main layout wrapper with top navigation
│   │   ├── ProtectedRoute.tsx # Auth guard, redirects unauthenticated users to /login
│   │   └── SuperAdminRoute.tsx # Role gate for admin panel
│   ├── hooks/
│   │   └── useAuth.ts         # Auth context: decodes JWT, manages login/logout state
│   ├── pages/
│   │   ├── LoginPage.tsx      # Google OAuth login form
│   │   ├── DashboardPage.tsx  # League list, create/join league entry point
│   │   ├── CreateLeaguePage.tsx # New league creation wizard
│   │   ├── LeaguePage.tsx     # League settings, member list, leaderboard tab
│   │   ├── DraftPage.tsx      # Castaway selection interface with pick availability
│   │   ├── RosterPage.tsx     # Player's own roster with perk controls
│   │   ├── RosterViewPage.tsx # Read-only view of another member's roster
│   │   ├── AdminPage.tsx      # Superadmin panel (leagues, scoring config, rescore)
│   │   └── InfoPage.tsx       # Season info, episode schedule, scoring rules
│   ├── App.tsx                # Root router: defines all routes and guards
│   ├── main.tsx               # Entry point, QueryClient setup, Google OAuth provider
│   └── index.css              # Global Tailwind directives and custom base styles
├── index.html                 # Vite HTML entry
├── package.json
├── tsconfig.json
├── tailwind.config.js         # Custom color theme
└── vite.config.ts             # Dev server proxy to backend
```

## Getting Started

### Prerequisites

- Node.js 20+
- npm 9+
- Backend API running on port 8000 (see `../backend/README.md`)

### Install Dependencies

```bash
cd frontend
npm install
```

### Environment Variables

Create a `.env` file in this directory:

```env
VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id
```

The `VITE_GOOGLE_CLIENT_ID` must match the client ID registered in Google Cloud Console with your app's origin in the allowed JavaScript origins.

### Development

```bash
npm run dev
```

The app runs at `http://localhost:5173`. Requests to `/api/*` are proxied to `http://localhost:8000` automatically (configured in `vite.config.ts`).

### Build for Production

```bash
npm run build
```

Output goes to `dist/`. In production this is served by Nginx inside the Docker container.

### Type Check

```bash
npm run tsc --noEmit
```

## Authentication

Authentication uses Google OAuth 2.0 with JWT tokens issued by the backend.

### Login Flow

1. User clicks "Sign in with Google" on `LoginPage.tsx`
2. Google OAuth dialog opens via `@react-oauth/google`
3. On success, the Google `id_token` is sent to `POST /api/v1/auth/google/`
4. Backend validates the token with Google, creates or updates the user, and returns access + refresh JWTs
5. Tokens are stored in `localStorage` under `sp_access` and `sp_refresh`
6. All subsequent API calls include `Authorization: Bearer <access_token>`

### Token Refresh

The Axios instance in `src/api/client.ts` automatically handles expired access tokens:

- On a 401 response, the interceptor calls `POST /api/v1/auth/token/refresh/` with the stored refresh token
- If refresh succeeds, the original request is retried with the new token
- If refresh fails (token expired or invalid), the user is logged out and redirected to `/login`

### User Profile

`useAuth.ts` decodes the JWT payload to expose:

```ts
{
  id: number
  email: string
  display_name: string
  avatar_url: string
  is_superadmin: boolean
}
```

## Routing

Defined in `App.tsx`:

| Path | Page | Access |
|------|------|--------|
| `/login` | LoginPage | Public |
| `/` | DashboardPage | Authenticated |
| `/leagues/new` | CreateLeaguePage | Authenticated |
| `/leagues/:slug` | LeaguePage | Authenticated |
| `/leagues/:slug/draft` | DraftPage | Authenticated |
| `/leagues/:slug/roster` | RosterPage | Authenticated |
| `/leagues/:slug/roster/:userId` | RosterViewPage | Authenticated |
| `/admin` | AdminPage | Superadmin only |
| `/info` | InfoPage | Authenticated |

`ProtectedRoute` redirects to `/login` if the user has no valid JWT. `SuperAdminRoute` redirects to `/` if the user is not a superadmin.

## Data Fetching

All server state is managed by TanStack Query. The query hooks live in `src/api/`:

### `leagues.ts` — League & Draft Hooks

| Hook | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `useLeagues` | GET | `/api/v1/leagues/` | List the current user's leagues |
| `useLeague` | GET | `/api/v1/leagues/:slug/` | Single league detail with members |
| `useCreateLeague` | POST | `/api/v1/leagues/` | Create a new league |
| `useJoinLeague` | POST | `/api/v1/leagues/join/` | Join a league by invite code |
| `useDraft` | GET | `/api/v1/leagues/:slug/draft/` | Draft state (open, current picks) |
| `useSaveDraft` | PUT | `/api/v1/leagues/:slug/draft/` | Save castaway selections |
| `useAvailableCastaways` | GET | `/api/v1/leagues/:slug/available-castaways/` | Castaways available to pick |
| `useRoster` | GET | `/api/v1/leagues/:slug/roster/` | Current user's roster |
| `useMemberRoster` | GET | `/api/v1/leagues/:slug/roster/:userId/` | Another member's roster |
| `useLeaderboard` | GET | `/api/v1/leagues/:slug/leaderboard/` | Rankings with episode scores |
| `useMyScores` | GET | `/api/v1/leagues/:slug/scores/` | Current user's episode score breakdown |
| `useActivity` | GET | `/api/v1/leagues/:slug/activity/` | Draft/perk event timeline |
| `useSwapPerk` | POST | `/api/v1/leagues/:slug/roster/swap/` | Use swap perk (replace a castaway) |
| `useBoostPerk` | POST | `/api/v1/leagues/:slug/roster/boost/` | Use boost perk (2x on one episode) |
| `useDraftWindow` | PATCH | `/api/v1/leagues/:slug/draft-window/` | Override draft open/close (owner) |

### `info.ts` — Public Info Hooks

| Hook | Endpoint | Description |
|------|----------|-------------|
| `useActiveSeason` | `/api/v1/active-season/` | Current season number, name, episodes |
| `useScoringConfig` | `/api/v1/scoring-config/` | Point values for every event type |

### `admin.ts` — Superadmin Hooks

| Hook | Endpoint | Description |
|------|----------|-------------|
| `useAdminLeagues` | `/api/v1/admin/leagues/` | All leagues (test + production) |
| `useCreateTestLeague` | POST `/api/v1/admin/leagues/` | Create a test league |
| `useAdminScoringConfig` | `/api/v1/admin/scoring-config/` | Load scoring config JSON |
| `useSaveScoringConfig` | PUT `/api/v1/admin/scoring-config/` | Save scoring config JSON |
| `useScoringSummary` | `/api/v1/admin/seasons/:n/scoring-summary/` | Events and totals per episode |
| `useRescore` | POST `/api/v1/admin/rescore/:n/` | Recalculate all rosters for a season |
| `useScoreUnscored` | POST `/api/v1/admin/score-unscored/:n/` | Score all past unscored episodes |

### Caching Strategy

- Default stale time: 5 minutes
- Default retry: 1 attempt
- League detail refetches every 30 seconds during draft phase (polling for member status)
- Mutations invalidate related queries automatically (e.g., saving draft invalidates leaderboard)

## Pages

### DashboardPage

- Lists leagues the user belongs to
- "Create League" button links to `/leagues/new`
- "Join League" form accepts an invite code
- Empty state guides new users to create or join their first league

### LeaguePage

Three tabs:

1. **Settings** — League name, invite code (copy-to-clipboard), draft window controls (owner only)
2. **Members** — List of all members with draft status indicators
3. **Leaderboard** — Ranked table of members with total points, expandable episode breakdown, score charts

Leaderboard hides rosters during the draft phase to prevent copying picks. After the draft closes, full transparency is shown.

### DraftPage

- Grid of all castaways for the active season with photos, names, ages, and occupations
- Players select exactly 5 castaways
- "Save Draft" button calls `useSaveDraft`
- Visual indicator for eliminated castaways (still draftable but shown differently)
- Disabled after draft window closes

### RosterPage

- Shows the user's 5 drafted castaways with live scores per episode
- **Swap Perk**: Replaces one castaway with any other (available once per roster, before draft closes)
- **Boost Perk**: Applies a 2x points multiplier to one specific episode (locked in after episode airs)
- Perk availability and usage state driven by API response

### AdminPage (Superadmin)

- View and filter all leagues
- Create test leagues that bypass draft-date restrictions
- Edit `scoring_config.json` in a JSON editor
- Trigger a full rescore for the active season
- Manually score any unscored past episodes
- View a scoring summary table (events detected per episode, castaway point totals)

## Styling

Tailwind CSS with a custom color palette defined in `tailwind.config.js`:

| Token | Hex | Usage |
|-------|-----|-------|
| `survivor-orange` | `#E8521A` | Primary actions, highlights |
| `survivor-dark` | `#1A1A2E` | Dark backgrounds, nav |
| `survivor-gold` | `#F0A500` | Accent, score highlights |

Global styles are in `src/index.css` using Tailwind's `@layer base` and `@layer components` directives.

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_GOOGLE_CLIENT_ID` | Yes | Google OAuth 2.0 client ID |

In development, Vite proxies all `/api` requests to `http://localhost:8000` so no additional API URL config is needed. In production, Nginx handles routing (see `../infra/README.md`).
