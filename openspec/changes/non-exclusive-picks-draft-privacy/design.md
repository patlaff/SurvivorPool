# Design: Non-Exclusive Picks & Draft Privacy

## Backend

### 1 — Remove pick exclusivity

**`DraftView.put`** — `backend/apps/leagues/views.py`

Delete the "already taken" block entirely:
```python
# REMOVE this entire block:
already_taken = RosterSlot.objects.filter(
    roster__league=league,
    castaway__castaway_id__in=castaway_ids,
).exclude(roster__user=request.user)
if already_taken.exists():
    taken_names = list(already_taken.values_list('castaway__name', flat=True))
    return Response(
        {'detail': f'Already drafted by another player: {", ".join(taken_names)}'},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

**`AvailableCastawaysView`** — `backend/apps/leagues/views.py`

The view currently filters out all castaways that appear in any roster. With non-exclusive picks this filtering is wrong. Simplify to always return all castaways in the season (still respecting elimination for non-test leagues):
```python
class AvailableCastawaysView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        league = _get_league_for_member(slug, request.user)
        castaways = Castaway.objects.filter(season=league.season)
        return Response(CastawaySerializer(castaways, many=True).data)
```
Note: the DraftPage uses `useSeasonCastaways` (not `useAvailableCastaways`) so this change primarily cleans up a now-incorrect endpoint; the frontend already behaves correctly.

---

### 2 — Roster privacy during draft window

A helper is needed in several views:

```python
def _draft_is_open(league):
    """Thin alias so views don't import utils directly."""
    from .utils import is_draft_open
    return is_draft_open(league)
```
(Or just use the existing `is_draft_open` import.)

**`RosterView.get`** — `backend/apps/leagues/views.py`

When `user_id` is provided (i.e., viewing *another* player's roster) and the draft is open, return 403:
```python
def get(self, request, slug, user_id=None):
    league = _get_league_for_member(slug, request.user)
    if user_id:
        # Viewing another member's roster — only allowed once draft is closed
        if is_draft_open(league):
            return Response(
                {'detail': "Other players' rosters are hidden until the draft closes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        roster = get_object_or_404(Roster, league=league, user_id=user_id)
    else:
        roster = get_object_or_404(Roster, league=league, user=request.user)
    return Response(RosterSerializer(roster).data)
```

**`LeaderboardView.get`** — `backend/apps/leagues/views.py`

When the draft is open, strip out the per-episode scores and castaway details from *other* players' entries. The requester's own entry remains fully visible (they can see their own points). Other entries show only rank, user info, and total points — no episode breakdown, no roster composition.

```python
def get(self, request, slug):
    league = _get_league_for_member(slug, request.user)
    draft_open = is_draft_open(league)
    ...
    for rank, entry in enumerate(entries, start=1):
        is_own = entry['user'].id == request.user.id
        results.append({
            'rank': rank,
            'user': {...},
            'total_points': entry['total_points'],
            # Hide episode breakdown for others while draft is open
            'episodes': EpisodeScoreSerializer(entry['episodes'], many=True).data
                        if (not draft_open or is_own) else [],
            'roster_hidden': draft_open and not is_own,
        })
    return Response({'entries': results, 'last_scored_at': last_scored, 'draft_open': draft_open})
```

**`LeagueActivityView.get`** — `backend/apps/leagues/views.py`

Draft-save events reveal picks. Hide `DraftSave` events (the `draft_saved` type) while the draft is open; swap and boost events remain visible since they only fire after the draft closes anyway.

```python
# In the draft saves loop:
if not is_draft_open(league):
    for ds in DraftSave.objects.filter(...):
        events.append({...})
```

---

## Frontend

### `RosterPage` — `frontend/src/pages/RosterPage.tsx`

Already only shows the *current user's* own roster (`GET /leagues/<slug>/roster/` with no user_id). No change needed.

### `RosterViewPage` — `frontend/src/pages/RosterViewPage.tsx`

This page renders another player's roster (`GET /leagues/<slug>/roster/<userId>/`). When the server returns 403 (draft is open), display a friendly message instead of an error:
```tsx
if (isError) {
  const msg = (error as AxiosError<{detail:string}>)?.response?.data?.detail
  if (msg?.includes('hidden')) {
    return <div className="card text-center py-12 text-gray-500">
      <p className="text-lg font-medium">Rosters are hidden during the draft window.</p>
      <p className="text-sm mt-1">Check back once the draft closes.</p>
    </div>
  }
}
```

### `LeaguePage` — `frontend/src/pages/LeaguePage.tsx`

The leaderboard table currently links to each player's roster page. While `draft_open` is true, disable those links (or remove them) and show a lock icon:
```tsx
// In the leaderboard row:
{draft_open
  ? <span className="flex items-center gap-2">{avatar}{entry.user.display_name} 🔒</span>
  : <Link to={`/leagues/${slug}/roster/${entry.user.id}`}>...</Link>
}
```

Also, the `roster_hidden` flag in each entry drives whether the per-episode columns render:
- If `entry.roster_hidden === true`: show `—` in episode cells (no scores revealed)
- Otherwise: show scores as normal

The leaderboard response also now includes `draft_open`; update the `LeaderboardResponse` type:
```ts
export interface LeaderboardResponse {
  entries: LeaderboardEntry[]
  last_scored_at: string | null
  draft_open: boolean
}
```
And add `roster_hidden: boolean` to `LeaderboardEntry`.

---

## Files changed

| File | Change |
|------|--------|
| `backend/apps/leagues/views.py` | Remove exclusivity check in `DraftView.put`; simplify `AvailableCastawaysView`; add draft-open guard to `RosterView`; add `roster_hidden` + strip episodes in `LeaderboardView`; hide draft-save events in `LeagueActivityView` while draft is open |
| `frontend/src/api/leagues.ts` | Add `roster_hidden: boolean` to `LeaderboardEntry`; add `draft_open: boolean` to `LeaderboardResponse` |
| `frontend/src/pages/LeaguePage.tsx` | Disable roster links + hide episode scores when `roster_hidden`; lock icon while draft open |
| `frontend/src/pages/RosterViewPage.tsx` | Handle 403 "hidden during draft" gracefully |
