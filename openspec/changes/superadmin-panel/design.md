# Design: Superadmin Panel

## 1. Superadmin identity

### Settings
Add to `config/settings.py` (reads from env, falls back to the default email):
```python
SUPERADMIN_EMAILS = env.list('SUPERADMIN_EMAILS', default=['patlaff728@gmail.com'])
```

### Custom JWT token class (`apps/accounts/tokens.py`)
Extend `RefreshToken` to embed additional claims in the access token so the frontend has them without an extra API call — including the fix for the current page-reload bug where display_name/avatar are empty:
```python
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

class SurvivorPoolRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token.access_token['email'] = user.email
        token.access_token['display_name'] = user.display_name
        token.access_token['avatar_url'] = user.avatar_url
        superadmin_emails = getattr(settings, 'SUPERADMIN_EMAILS', [])
        token.access_token['is_superadmin'] = user.email in superadmin_emails
        return token
```

Update `GoogleLoginView` to use `SurvivorPoolRefreshToken.for_user(user)` instead of `RefreshToken.for_user(user)`.

### DRF permission class (`apps/admin_panel/permissions.py`)
```python
from rest_framework.permissions import BasePermission
from django.conf import settings

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.email in getattr(settings, 'SUPERADMIN_EMAILS', [])
        )
```

### Frontend: `AuthUser` + `useAuth`
- Add `is_superadmin: boolean` to `AuthUser` interface
- Update `decodeUser` to read `is_superadmin`, `email`, `display_name`, `avatar_url` from JWT payload (fixing the existing page-reload bug at the same time)
- Add `SuperAdminRoute` component that renders `<Navigate to="/" />` if `!user?.is_superadmin`

---

## 2. Test leagues (`League.is_test`)

### Model change
Add `is_test = models.BooleanField(default=False, help_text='Relaxed restrictions for testing.')` to `League`. New migration required.

### Restriction bypasses
| Guard | Normal league | Test league |
|---|---|---|
| Draft window (`is_draft_open`) | enforced | skipped |
| Already taken by another roster | enforced | skipped |
| Available castaways (excludes eliminated) | enforced | returns all season castaways |
| Swap merge window | enforced | skipped |
| Boost aired-episode check | enforced | skipped |
| Boost scored-episode check | enforced | skipped |

Implementation: add `if not league.is_test:` guard around each existing check in `DraftView.put`, `AvailableCastawaysView.get`, `SwapPerkView.post`, and `BoostPerkView.post`.

---

## 3. Backend: new `apps/admin_panel` app

A dedicated app keeps admin logic isolated. Register in `INSTALLED_APPS` and wire into `config/urls.py` under `/api/v1/admin/`.

### Endpoints

#### `GET /api/v1/admin/leagues/`
Returns all leagues, ordered by `created_at` descending. Each entry includes `id`, `name`, `slug`, `owner` (display_name + email), `member_count`, `is_test`, `draft_open` (via `is_draft_open()`), `invite_code`, `created_at`.

#### `POST /api/v1/admin/leagues/`
Create a test league. Body: `{ "name": "..." }`. Creates a League with `is_test=True`, auto-assigns it to the active US season, creates a Membership for the requesting superadmin, and returns the full league detail including `slug` and `invite_code`.

#### `GET /api/v1/admin/seasons/{season_number}/scoring-summary/`
Returns all `ScoringEvent` rows for the season, organised as:
```json
{
  "season_number": 50,
  "scored_episodes": [
    {
      "episode_number": 1,
      "air_date": "2024-02-28",
      "scored_at": "2024-02-28T22:00:00Z",
      "events": [
        { "castaway_id": "...", "castaway_name": "...", "event_name": "...", "points": 20 }
      ],
      "episode_total": 245
    }
  ],
  "castaway_totals": [
    { "castaway_id": "...", "name": "...", "total_points": 310, "is_eliminated": false }
  ]
}
```

#### `GET /api/v1/admin/scoring-config/`
Reads `scoring_config.json` from `settings.SCORING_CONFIG_PATH` (or the default path). Returns `{ "config": { "event_name": points, ... } }`.

#### `PUT /api/v1/admin/scoring-config/`
Accepts `{ "config": { "event_name": points, ... } }`. Validates all values are non-negative integers. Writes atomically (write to `.tmp`, then rename). Returns the saved config.

#### `POST /api/v1/admin/rescore/{season_number}/`
Re-scores all previously-scored episodes for the season without re-fetching survivoR data:
1. Load config from disk.
2. For each `ScoringEvent` for the season, update `.points` from config (skip unknown event names, warn).
3. For each `Roster` in the season, recalculate `PlayerEpisodeScore.raw_points` and `final_points` (re-applying the Boost multiplier).
4. Returns `{ "episodes_rescored": N, "rosters_updated": M }`.

---

## 4. Frontend: `/admin` page

Route: `/admin`, protected by `SuperAdminRoute`.

Four sections rendered as tabs (or collapsible panels):

### 4.1 All Leagues
Table columns: Name (link to `/leagues/:slug`), Owner, Members, Draft Status, Test badge, Created.

### 4.2 Create Test League
Single name input + "Create Test League" button. On success, show the invite code and a link to the new league.

### 4.3 Season Scoring Summary
- Season selector (or default to active season).
- Per-episode accordion: header = "Episode N — YYYY-MM-DD | X events | Y pts total". Expanded body = table of castaway → event → points.
- Castaway totals table below: sorted by total points descending, with eliminated badge.

### 4.4 Scoring Config
- Editable table: event name (read-only) | point value (number input).
- "Save Config" button → PUT to `/admin/scoring-config/`.
- "Re-score Season" button → POST to `/admin/rescore/{season_number}/` — shows result toast.

---

## 5. LeagueSerializer: expose `is_test`

Add `is_test` to `LeagueSerializer` fields so test badges show correctly on the dashboard and league page.
