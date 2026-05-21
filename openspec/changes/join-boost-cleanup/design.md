# Design: Join & Boost Cleanup

## 1. Remove slug from Join League form

### Problem
`POST /leagues/{slug}/join/` requires the league slug in the URL path. The frontend currently exposes this as a user-facing input. Users don't know slugs — they only have invite codes.

### Solution
Add a new backend endpoint `POST /api/v1/leagues/join/` that accepts only `{ "invite_code": "..." }`, looks up the league by invite code, and performs the join. This removes the slug requirement from the user-facing flow entirely.

**New endpoint:**
```
POST /api/v1/leagues/join/
Body: { "invite_code": "ABCD1234" }
Success: 200 { "detail": "Joined successfully.", "slug": "<league-slug>" }
Errors:
  400 — invite code not found
  400 — already a member
```

The slug is returned in the success response so the frontend can redirect the user to the league page.

**Frontend changes (`DashboardPage.tsx`):**
- Remove `joinSlug` state and "League URL slug" input
- Update `handleJoin` to call the new `/leagues/join/` endpoint
- On success, optionally redirect to `/leagues/{slug}` using the returned slug
- Update `useJoinLeague` mutation in `leagues.ts` to POST to `/leagues/join/` with just `{ invite_code }`

### Keep old endpoint
`POST /leagues/{slug}/join/` stays in place (no breaking change).

---

## 2. Boost eligibility: aired episodes

### Problem
`boostEligible` is currently computed as episodes that are `!scored_at && !is_finale`. An episode that has aired but not yet been scored by the admin passes this filter — but it's too late to meaningfully boost it.

### Backend fix (`BoostPerkView.post`)
Add an air-date guard after the existing scored check:
```python
if episode.air_date <= timezone.now().date():
    return Response(
        {'detail': 'That episode has already aired.'},
        status=status.HTTP_400_BAD_REQUEST,
    )
```
Order of checks: perk used → already scored → already aired → is finale.

### Frontend fix (`RosterPage.tsx`)
Update the `boostEligible` filter to also exclude episodes whose `air_date` is today or in the past:
```ts
const today = new Date()
today.setHours(0, 0, 0, 0)
const boostEligible = episodes?.filter(e =>
  !e.scored_at &&
  !e.is_finale &&
  new Date(e.air_date) > today
) ?? []
```

(The `air_date` field is already present on `SeasonEpisode` from the episodes API.)
