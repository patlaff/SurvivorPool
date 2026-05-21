# Design: League Draft Window Control

## Data Model

Add two nullable fields to the existing `League` model:

```python
# apps/leagues/models.py

class League(models.Model):
    # ... existing fields ...

    # Per-league draft window overrides (both nullable = use season default)
    draft_close_at = models.DateTimeField(
        null=True, blank=True,
        help_text='If set, the draft closes at this datetime (overrides season lock date).'
    )
    draft_force_open = models.BooleanField(
        default=False,
        help_text='When True, the draft is open regardless of draft_close_at or season lock date.'
    )
```

**Draft-open resolution order** (first match wins):

1. `draft_force_open == True` → **open**
2. `draft_close_at` is set and `now >= draft_close_at` → **closed**
3. `draft_close_at` is set and `now < draft_close_at` → **open**
4. `season.draft_lock_date` is set and `today >= lock_date` → **closed**
5. Everything else → **open**

This logic replaces the existing `get_draft_open` serializer method and the `DraftView` lock check.

---

## Migration

New migration `leagues/migrations/0002_league_draft_window.py`:

```python
migrations.AddField('League', 'draft_close_at', models.DateTimeField(null=True, blank=True))
migrations.AddField('League', 'draft_force_open', models.BooleanField(default=False))
```

---

## Shared Draft-Open Helper

Extract the resolution logic into a single utility function used by both the serializer and the view, to avoid duplication:

```python
# apps/leagues/utils.py

from django.utils import timezone

def is_draft_open(league) -> bool:
    if league.draft_force_open:
        return True
    if league.draft_close_at is not None:
        return timezone.now() < league.draft_close_at
    lock_date = league.season.draft_lock_date
    if lock_date is None:
        return True
    return timezone.now().date() < lock_date
```

---

## API

### Existing endpoints — updated

`GET /api/v1/leagues/{slug}/` response now includes:

```json
{
  "draft_open": true,
  "draft_close_at": "2026-02-24T23:59:00Z",   // null if not set
  "draft_force_open": false
}
```

`LeagueSerializer.get_draft_open` and `LeagueSerializer.get_draft_lock_date` both delegate to `is_draft_open()`.

`DraftView.put` lock check also delegates to `is_draft_open()`.

### New endpoint

**`PATCH /api/v1/leagues/{slug}/draft-window/`**

- Permission: `IsLeagueOwner` (only the league owner may call this)
- Request body (all fields optional):

```json
{
  "draft_close_at": "2026-02-24T23:59:00Z",  // ISO 8601, or null to clear
  "draft_force_open": false
}
```

- Convenience shortcuts the frontend will use:
  - **Close now**: `{ "draft_close_at": "<now>", "draft_force_open": false }`
  - **Reopen**: `{ "draft_close_at": null, "draft_force_open": true }`
  - **Schedule close**: `{ "draft_close_at": "<future datetime>", "draft_force_open": false }`
  - **Revert to season default**: `{ "draft_close_at": null, "draft_force_open": false }`

- Response: updated `LeagueDetailSerializer` payload (200) or validation error (400).

- Validation:
  - If `draft_close_at` is in the past and `draft_force_open` is False, warn but allow (owner is intentionally closing).
  - No other constraints — owners have full autonomy.

---

## URL

```python
# apps/leagues/urls.py
path('leagues/<slug:slug>/draft-window/', DraftWindowView.as_view(), name='draft-window'),
```

---

## Frontend

### `api/leagues.ts`

- Extend `League` interface with `draft_close_at: string | null` and `draft_force_open: boolean`.
- Add `useDraftWindow(slug)` mutation hook calling `PATCH /leagues/{slug}/draft-window/`.

### `LeaguePage.tsx` — new "Draft Settings" panel

Shown only to the league owner (`user.id === league.owner.id`), rendered below the leaderboard/chart tabs.

```
┌─ Draft Settings ──────────────────────────────────────┐
│  Status:  ● Open  (closes Feb 24 at 11:59 PM)         │
│                                                        │
│  [Close draft now]  [Reopen draft]                     │
│                                                        │
│  Schedule close:  [date/time input]  [Set]  [Clear]    │
└────────────────────────────────────────────────────────┘
```

- **Status badge**: green "Open" or red "Closed", with the scheduled close time if `draft_close_at` is set.
- **Close now**: sets `draft_close_at` to the current time, `draft_force_open: false`.
- **Reopen**: sets `draft_close_at: null`, `draft_force_open: true`. Always enabled — `Season.draft_lock_date` is only a default and does not prevent an owner from reopening their league's draft.
- **Schedule close**: datetime-local input; on "Set" sends the chosen datetime.
- **Clear**: sends `draft_close_at: null, draft_force_open: false` (reverts to season default).
- All actions invalidate `['league', slug]` and `['draft', slug]` queries on success.

### `DraftPage.tsx`

No changes needed — already reads `draft_open` and `draft_close_at` from the `useDraft` hook response, and the backend now derives those correctly from the new fields.

---

## Permissions

`IsLeagueOwner` (already implemented in `apps/leagues/permissions.py`) — reused as-is.

Non-owners can read `draft_close_at` and `draft_force_open` from the league detail endpoint (needed so their DraftPage shows the correct countdown), but cannot write to the draft-window endpoint.
