# Design: Season Lifecycle Management

## Backend

### 1 — Fix `_sync_season`: enforce single active season

**File:** `backend/apps/scoring/tasks.py`

Before the `Season.objects.update_or_create(...)` call, deactivate all other US seasons:

```python
# Ensure exactly one US season is active at a time
Season.objects.filter(version='US').exclude(season_number=season_number).update(is_active=False)
season_obj, _ = Season.objects.update_or_create(
    season_number=season_number,
    defaults={'name': f'Survivor Season {season_number}', 'version': 'US', 'is_active': True},
)
```

---

### 2 — Add `is_archived` to `League`

**File:** `backend/apps/leagues/models.py`

```python
is_archived = models.BooleanField(
    default=False,
    help_text='True when the season has concluded. League becomes read-only.',
)
```

Run `makemigrations leagues` + `migrate` and copy migration to host.

---

### 3 — Expose `is_archived` in serializers

**File:** `backend/apps/leagues/serializers.py`

Add `'is_archived'` to both `LeagueSerializer` and `LeagueDetailSerializer` field lists.

---

### 4 — Guard write operations on archived leagues

**File:** `backend/apps/leagues/views.py`

Add a guard at the top of each write handler. The same check in three places:

```python
if league.is_archived:
    return Response(
        {'detail': 'This league has been archived and is now read-only.'},
        status=status.HTTP_403_FORBIDDEN,
    )
```

- `DraftView.put` — after the existing draft-open check
- `SwapPerkView.post` — before the perk-used check
- `BoostPerkView.post` — before the perk-used check

---

### 5 — Admin "Archive Season" endpoint

**File:** `backend/apps/admin_panel/views.py`

New view `AdminArchiveSeasonView`:

```python
class AdminArchiveSeasonView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, season_number):
        from django.utils import timezone
        season = get_object_or_404(Season, season_number=season_number, version='US')
        leagues = League.objects.filter(season=season)
        # Close all drafts and mark leagues as archived
        leagues.update(
            is_archived=True,
            draft_force_open=False,
            draft_close_at=timezone.now(),
        )
        count = leagues.count()
        return Response({'detail': f'Archived {count} league(s) for Season {season_number}.'})
```

**File:** `backend/apps/admin_panel/urls.py`

```python
path('admin/archive-season/<int:season_number>/', AdminArchiveSeasonView.as_view(), name='admin-archive-season'),
```

---

## Frontend

### 6 — AdminPage: replace hardcoded `ACTIVE_SEASON`

**File:** `frontend/src/pages/AdminPage.tsx`

- Import `useActiveSeason` from `../api/info`
- Inside the `ScoringTab` and `ConfigTab` components (or at the top of `AdminPage`), replace `const ACTIVE_SEASON = 50` with:
  ```tsx
  const { data: activeSeasonData } = useActiveSeason()
  const ACTIVE_SEASON = activeSeasonData?.season?.season_number ?? 0
  ```
- Guard any `mutateAsync` calls that use `ACTIVE_SEASON` — disable buttons when `ACTIVE_SEASON === 0`

Also add an "Archive Season" button in the admin panel (e.g. in `ScoringTab` below the scoring controls):

```tsx
<button
  className="btn-secondary text-xs px-3 py-1.5 text-red-600 border-red-300 hover:bg-red-50"
  onClick={() => archiveSeason.mutateAsync(ACTIVE_SEASON)}
  disabled={!ACTIVE_SEASON || archiveSeason.isPending}
>
  Archive Season {ACTIVE_SEASON}
</button>
```

Add `useArchiveSeason` hook to `frontend/src/api/admin.ts`:

```typescript
export function useArchiveSeason() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (seasonNumber: number) =>
      api.post(`/admin/archive-season/${seasonNumber}/`).then(r => r.data as { detail: string }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leagues'] }),
  })
}
```

---

### 7 — Dashboard: split active vs archived leagues

**File:** `frontend/src/pages/DashboardPage.tsx`

- Split `leagues` into `activeLeagues` (where `!league.is_archived`) and `archivedLeagues` (where `league.is_archived`)
- Render active leagues as before
- Render archived leagues in a collapsible section below: "Past Seasons ▾" (collapsed by default with a `useState` toggle)
- Archived league cards show a greyed-out "Archived" badge instead of the draft status badge

```tsx
const activeLeagues = leagues?.filter(l => !l.is_archived) ?? []
const archivedLeagues = leagues?.filter(l => l.is_archived) ?? []
const [showArchived, setShowArchived] = useState(false)
```

---

### 8 — LeaguePage: archived badge + hide action buttons

**File:** `frontend/src/pages/LeaguePage.tsx`

- Read `league?.is_archived` from the existing `useLeague` data
- Replace the two action buttons (Draft, My Roster) with an "Archived" badge when `is_archived`:
  ```tsx
  {league?.is_archived
    ? <span className="badge-gray">Archived</span>
    : <>
        <Link to={`/leagues/${slug}/draft`} className="btn-secondary">Draft</Link>
        <Link to={`/leagues/${slug}/roster`} className="btn-secondary">My Roster</Link>
      </>
  }
  ```
- Show a notice banner below the header:
  ```tsx
  {league?.is_archived && (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-6 text-sm text-gray-600">
      This league has concluded. All scores and rosters are preserved as a read-only record.
    </div>
  )}
  ```

---

## Files changed

| File | Change |
|------|--------|
| `backend/apps/scoring/tasks.py` | Deactivate other seasons before activating new one |
| `backend/apps/leagues/models.py` | Add `is_archived` field |
| `backend/apps/leagues/serializers.py` | Expose `is_archived` in both serializers |
| `backend/apps/leagues/views.py` | 403 guard in DraftView, SwapPerkView, BoostPerkView |
| `backend/apps/admin_panel/views.py` | New `AdminArchiveSeasonView` |
| `backend/apps/admin_panel/urls.py` | Register archive endpoint |
| `backend/apps/leagues/migrations/` | Generated migration |
| `frontend/src/api/admin.ts` | `useArchiveSeason` hook |
| `frontend/src/pages/AdminPage.tsx` | Replace hardcoded season; add Archive button |
| `frontend/src/pages/DashboardPage.tsx` | Split active/archived leagues |
| `frontend/src/pages/LeaguePage.tsx` | Archived badge + notice banner |
