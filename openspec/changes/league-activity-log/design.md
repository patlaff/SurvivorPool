# Design: League Activity Log

## Backend

### New model: `DraftSave`

Add to `apps/leagues/models.py`:

```python
class DraftSave(models.Model):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name='draft_saves')
    saved_at = models.DateTimeField(auto_now_add=True)
    castaway_names = models.JSONField(default=list)   # snapshot of names at save time

    class Meta:
        ordering = ['saved_at']
```

A new record is written every time `DraftView.put` completes successfully. `castaway_names` stores the ordered list of names (e.g. `["Alice", "Bob", "Charlie", "Dana", "Evan"]`) as a human-readable snapshot — no FK needed.

### Migration

Generate with `makemigrations leagues` and run `migrate`.

### `DraftView.put` — write audit record

After the `with transaction.atomic()` block (and after the score backfill), add:

```python
DraftSave.objects.create(
    roster=roster,
    castaway_names=[castaway_map[cid].name for cid in castaway_ids],
)
```

### New API endpoint: `LeagueActivityView`

`GET /api/v1/leagues/<slug>/activity/`

- Restricted to the league **owner** (403 otherwise).
- Queries three sources and merges into a single chronological list:

  1. **Draft saves** — `DraftSave.objects.filter(roster__league=league).select_related('roster__user')`
  2. **Swap perks** — `Perk.objects.filter(roster__league=league, perk_type=Perk.SWAP, used=True).select_related('roster__user', 'swapped_out_castaway', 'swapped_in_castaway')`
  3. **Boost perks** — `Perk.objects.filter(roster__league=league, perk_type=Perk.BOOST, used=True).select_related('roster__user')`

Response shape (array, newest first):

```json
[
  {
    "type": "draft_saved",
    "timestamp": "2026-03-02T14:35:00Z",
    "user": { "id": 2, "display_name": "Alice" },
    "detail": { "castaways": ["Bob", "Charlie", "Dana", "Evan", "Frank"] }
  },
  {
    "type": "swap_used",
    "timestamp": "2026-04-10T21:12:00Z",
    "user": { "id": 3, "display_name": "Ben" },
    "detail": { "dropped": "Frank", "added": "Grace" }
  },
  {
    "type": "boost_used",
    "timestamp": "2026-04-09T18:00:00Z",
    "user": { "id": 2, "display_name": "Alice" },
    "detail": { "episode": 9 }
  }
]
```

---

## Frontend

### API hook — `useLeagueActivity`

New file: `frontend/src/api/admin.ts` is for superadmin — this goes in `frontend/src/api/leagues.ts`.

```ts
export interface ActivityEvent {
  type: 'draft_saved' | 'swap_used' | 'boost_used'
  timestamp: string
  user: { id: number; display_name: string; avatar_url?: string }
  detail: Record<string, unknown>
}

export function useLeagueActivity(slug: string, enabled: boolean) {
  return useQuery<ActivityEvent[]>({
    queryKey: ['league-activity', slug],
    queryFn: () => api.get(`/leagues/${slug}/activity/`).then(r => r.data),
    enabled,
  })
}
```

`enabled` is passed as `isOwner` from the component so non-owners never fire the request.

### `LeaguePage` changes

- Add `'activity'` to the `tab` union type: `'leaderboard' | 'chart' | 'activity'`
- Add a third tab button visible only when `isOwner`:
  ```tsx
  {isOwner && (
    <button ... onClick={() => setTab('activity')}>Activity Log</button>
  )}
  ```
- Mount `useLeagueActivity(slug!, isOwner && tab === 'activity')` — or always `isOwner`; fetching on tab change is acceptable.
- Render `<ActivityLogTab events={activityData} isLoading={activityLoading} />` when `tab === 'activity' && isOwner`.

### `ActivityLogTab` component (inline in `LeaguePage.tsx`)

Renders a vertical timeline. Each entry shows:
- **Icon** indicating type (🗳 draft, 🔄 swap, ⚡ boost)
- **User name** + relative or absolute timestamp (use a `toLocaleString` formatter)
- **Detail line**: for drafts, the comma-joined list of castaways; for swaps, "dropped X, added Y"; for boosts, "doubled Ep N"

Empty state: "No activity yet."

---

## Files changed

| File | Change |
|------|--------|
| `backend/apps/leagues/models.py` | Add `DraftSave` model |
| `backend/apps/leagues/migrations/NNNN_add_draftsave.py` | Auto-generated |
| `backend/apps/leagues/views.py` | Write `DraftSave` in `DraftView.put`; add `LeagueActivityView` |
| `backend/apps/leagues/urls.py` | Register `leagues/<slug>/activity/` |
| `frontend/src/api/leagues.ts` | Add `ActivityEvent` interface + `useLeagueActivity` |
| `frontend/src/pages/LeaguePage.tsx` | Add Activity Log tab + render logic |
