# Tasks: League Activity Log

## Task 1 — Add `DraftSave` model and migration

**File:** `backend/apps/leagues/models.py`

- [x] Add `DraftSave` model after the `RosterSlot` class:
  ```python
  class DraftSave(models.Model):
      roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name='draft_saves')
      saved_at = models.DateTimeField(auto_now_add=True)
      castaway_names = models.JSONField(default=list)

      class Meta:
          ordering = ['saved_at']

      def __str__(self):
          return f'DraftSave for {self.roster} at {self.saved_at}'
  ```

**Migration:**
- [x] Run `python manage.py makemigrations leagues` inside the container to generate the migration
- [x] Run `python manage.py migrate` to apply it
- [x] Verify migration file is present at `backend/apps/leagues/migrations/NNNN_add_draftsave.py`

Test: `DraftSave.objects.create(roster=some_roster, castaway_names=['A','B','C','D','E'])` should succeed in the Django shell.

---

## Task 2 — Write `DraftSave` record in `DraftView.put`

**File:** `backend/apps/leagues/views.py`

- [x] Import `DraftSave` at the top of the method (or at module level alongside other model imports)
- [x] After the score-backfill block and before `return Response({'detail': 'Draft saved.'})`, add:
  ```python
  DraftSave.objects.create(
      roster=roster,
      castaway_names=[castaway_map[cid].name for cid in castaway_ids],
  )
  ```

Test: After calling `PUT /leagues/<slug>/draft/` with valid picks, query `DraftSave.objects.filter(roster__league__slug=slug)` in the shell — expect one new row per call.

---

## Task 3 — Add `LeagueActivityView`

**File:** `backend/apps/leagues/views.py`

- [x] Add `LeagueActivityView` class after `DraftWindowView`:
  ```python
  class LeagueActivityView(APIView):
      permission_classes = [IsAuthenticated]

      def get(self, request, slug):
          league = get_object_or_404(League, slug=slug)
          if league.owner != request.user:
              return Response({'detail': 'Only the league owner can view the activity log.'}, status=status.HTTP_403_FORBIDDEN)

          events = []

          # Draft saves
          for ds in DraftSave.objects.filter(roster__league=league).select_related('roster__user').order_by('saved_at'):
              events.append({
                  'type': 'draft_saved',
                  'timestamp': ds.saved_at,
                  'user': {
                      'id': ds.roster.user.id,
                      'display_name': ds.roster.user.display_name,
                      'avatar_url': ds.roster.user.avatar_url,
                  },
                  'detail': {'castaways': ds.castaway_names},
              })

          # Swap perks
          for perk in Perk.objects.filter(
              roster__league=league, perk_type=Perk.SWAP, used=True,
          ).select_related('roster__user', 'swapped_out_castaway', 'swapped_in_castaway').order_by('used_at'):
              events.append({
                  'type': 'swap_used',
                  'timestamp': perk.used_at,
                  'user': {
                      'id': perk.roster.user.id,
                      'display_name': perk.roster.user.display_name,
                      'avatar_url': perk.roster.user.avatar_url,
                  },
                  'detail': {
                      'dropped': perk.swapped_out_castaway.name if perk.swapped_out_castaway else None,
                      'added': perk.swapped_in_castaway.name if perk.swapped_in_castaway else None,
                  },
              })

          # Boost perks
          for perk in Perk.objects.filter(
              roster__league=league, perk_type=Perk.BOOST, used=True,
          ).select_related('roster__user').order_by('used_at'):
              events.append({
                  'type': 'boost_used',
                  'timestamp': perk.used_at,
                  'user': {
                      'id': perk.roster.user.id,
                      'display_name': perk.roster.user.display_name,
                      'avatar_url': perk.roster.user.avatar_url,
                  },
                  'detail': {'episode': perk.boost_target_episode},
              })

          events.sort(key=lambda e: e['timestamp'] or '', reverse=True)
          return Response(events)
  ```

Test: `GET /api/v1/leagues/<slug>/activity/` as owner → 200 with list. As non-owner → 403.

---

## Task 4 — Register activity URL

**File:** `backend/apps/leagues/urls.py`

- [x] Import `LeagueActivityView` from `.views`
- [x] Add `path('leagues/<slug:slug>/activity/', LeagueActivityView.as_view(), name='league-activity')` in `urlpatterns`

Test: Curl the endpoint with a valid owner token → 200 JSON.

---

## Task 5 — Frontend API hook

**File:** `frontend/src/api/leagues.ts`

- [x] Add `ActivityEvent` interface:
  ```ts
  export interface ActivityEvent {
    type: 'draft_saved' | 'swap_used' | 'boost_used'
    timestamp: string
    user: { id: number; display_name: string; avatar_url: string }
    detail: Record<string, unknown>
  }
  ```
- [x] Add `useLeagueActivity` hook:
  ```ts
  export function useLeagueActivity(slug: string, enabled: boolean) {
    return useQuery<ActivityEvent[]>({
      queryKey: ['league-activity', slug],
      queryFn: () => api.get(`/leagues/${slug}/activity/`).then(r => r.data),
      enabled,
    })
  }
  ```

---

## Task 6 — Activity Log tab in `LeaguePage`

**File:** `frontend/src/pages/LeaguePage.tsx`

- [x] Update `tab` type to `'leaderboard' | 'chart' | 'activity'`
- [x] Call `useLeagueActivity(slug!, isOwner)` (always enabled for owners, disabled for others)
- [x] Add tab button after the chart button, rendered only when `isOwner`:
  ```tsx
  {isOwner && (
    <button
      className={`pb-2 text-sm font-medium ${tab === 'activity' ? 'border-b-2 border-survivor-orange text-survivor-orange' : 'text-gray-500'}`}
      onClick={() => setTab('activity')}
    >
      Activity Log
    </button>
  )}
  ```
- [x] Add inline `ActivityLogTab` component and render it when `tab === 'activity' && isOwner`:
  - Displays a vertical timeline (newest entry first)
  - Each row: icon + user display name + formatted timestamp + detail text
  - Icons: `🗳` for draft_saved, `🔄` for swap_used, `⚡` for boost_used
  - Detail text:
    - `draft_saved`: "Saved picks: Alice, Bob, Charlie, Dana, Evan"
    - `swap_used`: "Swapped out Charlie → added Grace"
    - `boost_used`: "Doubled points for Ep 9"
  - Timestamp: `new Date(event.timestamp).toLocaleString()`
  - Empty state: "No activity yet in this league."
  - Loading state: "Loading activity…"

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — DraftSave model + migration | — |
| 2 — Write DraftSave in DraftView.put | 1 |
| 3 — LeagueActivityView | 1 |
| 4 — Register URL | 3 |
| 5 — Frontend hook | — |
| 6 — LeaguePage tab | 4, 5 |
