# Tasks: Join & Boost Cleanup

## Fix 1 — Remove slug from Join League

### 1.1 New backend endpoint
- [x] Add `LeagueJoinByCodeView(APIView)` in `apps/leagues/views.py`:
  - `POST`: accept `{ "invite_code": "..." }`, look up league by `invite_code`, call `Membership.objects.get_or_create`, return `{ "detail": "Joined successfully.", "slug": league.slug }` or appropriate 400
- [x] Register `path('leagues/join/', LeagueJoinByCodeView.as_view(), name='league-join-by-code')` in `apps/leagues/urls.py` — must appear **before** the `leagues/<slug:slug>/` pattern

### 1.2 Frontend API hook update
- [x] In `frontend/src/api/leagues.ts`, update `useJoinLeague` mutation:
  - Change `mutationFn` to `POST /leagues/join/` with `{ invite_code }` only (drop `slug` param)
  - Return type includes `slug: string` from the response
  - Keep `onSuccess` query invalidation

### 1.3 DashboardPage UI update
- [x] In `frontend/src/pages/DashboardPage.tsx`:
  - Remove `joinSlug` state and setter
  - Remove the "League URL slug" `<label>` + `<input>` block
  - Remove `slug: joinSlug` from the `mutateAsync` call
  - Remove `setJoinSlug('')` from reset logic

---

## Fix 2 — Boost only on future (un-aired) episodes

### 2.1 Backend guard
- [x] In `apps/leagues/views.py` `BoostPerkView.post`, after the `scored_at` check and before the `is_finale` check, add:
  ```python
  if episode.air_date <= timezone.now().date():
      return Response(
          {'detail': 'That episode has already aired.'},
          status=status.HTTP_400_BAD_REQUEST,
      )
  ```

### 2.2 Frontend eligibility filter
- [x] In `frontend/src/pages/RosterPage.tsx`, update `boostEligible` computation:
  ```ts
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const boostEligible = episodes?.filter(e =>
    !e.scored_at &&
    !e.is_finale &&
    new Date(e.air_date) > today
  ) ?? []
  ```

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1.1 New endpoint | — |
| 1.2 API hook update | 1.1 |
| 1.3 Dashboard UI | 1.2 |
| 2.1 Backend guard | — |
| 2.2 Frontend filter | — |
