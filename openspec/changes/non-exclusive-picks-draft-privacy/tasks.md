# Tasks: Non-Exclusive Picks & Draft Privacy

## Task 1 — Remove pick-exclusivity check from `DraftView.put`

**File:** `backend/apps/leagues/views.py`

- [x] Delete the `already_taken` block (the `RosterSlot.objects.filter(...).exclude(roster__user=request.user)` check and its `if already_taken.exists()` response)

Test: Two different users in the same league should both be able to `PUT /leagues/<slug>/draft/` with the same 5 `castaway_ids` and receive `{"detail": "Draft saved."}` from both.

---

## Task 2 — Simplify `AvailableCastawaysView`

**File:** `backend/apps/leagues/views.py`

- [x] Remove the `picked_ids` exclusion logic from the non-test branch so the view returns **all** castaways in the season (same as the `is_test` branch already does):
  ```python
  def get(self, request, slug):
      league = _get_league_for_member(slug, request.user)
      castaways = Castaway.objects.filter(season=league.season)
      return Response(CastawaySerializer(castaways, many=True).data)
  ```

Test: `GET /leagues/<slug>/available-castaways/` should return all castaways in the season regardless of how many rosters already exist.

---

## Task 3 — Block other-player roster access while draft is open

**File:** `backend/apps/leagues/views.py`

- [x] In `RosterView.get`, when `user_id` is provided and `is_draft_open(league)` is `True`, return:
  ```python
  return Response(
      {'detail': "Other players' rosters are hidden until the draft closes."},
      status=status.HTTP_403_FORBIDDEN,
  )
  ```
  Own-roster requests (`user_id=None`) are always allowed.

Test:
- `GET /leagues/<slug>/roster/<other_user_id>/` while draft open → 403
- `GET /leagues/<slug>/roster/<other_user_id>/` after draft closes → 200
- `GET /leagues/<slug>/roster/` (own) while draft open → 200

---

## Task 4 — Add `roster_hidden` + `draft_open` to `LeaderboardView`

**File:** `backend/apps/leagues/views.py`

- [x] Import `is_draft_open` at the top of `LeaderboardView.get` (already imported at module level — just use it)
- [x] Compute `draft_open = is_draft_open(league)` once at the top of the view
- [x] For each entry, add `roster_hidden: bool` — `True` when `draft_open` and the entry is not the requesting user
- [x] Strip episode scores (`episodes: []`) for entries where `roster_hidden` is `True`
- [x] Include `draft_open` in the top-level response dict

```python
draft_open = is_draft_open(league)
...
is_own = entry['user'].id == request.user.id
roster_hidden = draft_open and not is_own
results.append({
    ...
    'episodes': EpisodeScoreSerializer(entry['episodes'], many=True).data if not roster_hidden else [],
    'roster_hidden': roster_hidden,
})
return Response({'entries': results, 'last_scored_at': last_scored, 'draft_open': draft_open})
```

Test: Call leaderboard as user A while draft is open → own entry has episodes, other entries have `episodes: []` and `roster_hidden: true`.

---

## Task 5 — Hide draft-save events in `LeagueActivityView` while draft is open

**File:** `backend/apps/leagues/views.py`

- [x] Wrap the `DraftSave` loop in a check: only append draft-save events when `not is_draft_open(league)`

```python
if not is_draft_open(league):
    for ds in DraftSave.objects.filter(...).select_related(...).order_by('saved_at'):
        events.append({...})
```

Test: `GET /leagues/<slug>/activity/` while draft open → no `draft_saved` events in response. After draft closes → `draft_saved` events appear.

---

## Task 6 — Update TypeScript types

**File:** `frontend/src/api/leagues.ts`

- [x] Add `roster_hidden: boolean` to `LeaderboardEntry`
- [x] Add `draft_open: boolean` to `LeaderboardResponse`

---

## Task 7 — Leaderboard UI: disable roster links + hide scores while draft open

**File:** `frontend/src/pages/LeaguePage.tsx`

- [x] Read `draft_open` from `leaderboardData?.draft_open`
- [x] In the player name cell: when `draft_open` is true (and it's not the current user's own row), render the name with a 🔒 instead of a `<Link>`:
  ```tsx
  const isOwnRow = entry.user.id === user?.id
  // Name cell:
  {draft_open && !isOwnRow
    ? <span className="flex items-center gap-2">
        {avatar}{entry.user.display_name} <span className="text-gray-400 text-xs">🔒</span>
      </span>
    : <Link to={`/leagues/${slug}/roster/${entry.user.id}`}>...</Link>
  }
  ```
- [x] In the per-episode score cells: when `entry.roster_hidden` is `true`, render `—` instead of the score:
  ```tsx
  <td key={ep.episode_number} className="py-3 pr-2 text-right text-gray-600">
    {entry.roster_hidden ? <span className="text-gray-300">—</span> : (
      <>
        {ep.final_points > ep.raw_points && <span title="Boosted" className="text-survivor-gold mr-1">⚡</span>}
        {ep.final_points}
      </>
    )}
  </td>
  ```

Test: Open the league page while draft is open → other players' rows show 🔒 name (no link), episode cells show `—`. Own row still shows scores and links normally.

---

## Task 8 — `RosterViewPage`: handle draft-privacy 403 gracefully

**File:** `frontend/src/pages/RosterViewPage.tsx`

- [x] Import `AxiosError` (or use type assertion) to read the response detail
- [x] When the query is in error state, check if the response detail contains "hidden":
  ```tsx
  if (isError) {
    const detail = (error as {response?: {data?: {detail?: string}}})?.response?.data?.detail ?? ''
    if (detail.toLowerCase().includes('hidden')) {
      return (
        <div className="card text-center py-12 text-gray-500">
          <p className="text-xl">🔒</p>
          <p className="text-lg font-medium mt-2">Rosters are hidden during the draft window.</p>
          <p className="text-sm mt-1 text-gray-400">Check back once the draft closes.</p>
        </div>
      )
    }
  }
  ```

Test: Navigate to `/leagues/<slug>/roster/<other_user_id>` while draft is open → see the privacy message. After draft closes → see the roster normally.

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — Remove exclusivity check | — |
| 2 — Simplify AvailableCastawaysView | — |
| 3 — Block roster access while draft open | — |
| 4 — Leaderboard roster_hidden + draft_open | — |
| 5 — Hide draft-save events | — |
| 6 — TypeScript types | 4 |
| 7 — Leaderboard UI | 4, 6 |
| 8 — RosterViewPage 403 handling | 3 |
