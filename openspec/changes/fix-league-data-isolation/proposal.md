# Proposal: Fix League Data Isolation

## What

Users can see other users' leagues on the "My Leagues" dashboard when sharing a browser session. A user who logs out and is followed by a different user logging in will briefly see the first user's league list before the page refetches.

## Why

The TanStack Query cache is a **module-level singleton** (`queryClient` in `main.tsx`). On logout, `useAuth` only clears tokens and nulls out the user state — it never calls `queryClient.clear()`. With a 5-minute `staleTime`, cached league data from the previous user's session is immediately served to the next user who logs into the same browser tab.

The backend `LeagueListCreateView` already filters correctly (`memberships__user=self.request.user`), so this is purely a frontend cache isolation problem.

## Root Cause

```
User A logs in → fetches /leagues/ → cache: { ['leagues']: [LeagueA1, LeagueA2] }
User A logs out → tokens cleared, user=null, BUT cache untouched
User B logs in → TanStack Query serves stale ['leagues'] from cache → B sees A's leagues
B's own request fires → resolves correctly → cache updated
```

The window of exposure depends on the stale time (currently 5 minutes) and how fast the user navigates to the dashboard.

## Fix

1. **Clear the query cache on logout** — call `queryClient.clear()` inside `useAuth.logout()`. Since `useAuth` is already a React hook, it can call `useQueryClient()` to get the client instance.

2. **Scope user-specific query keys by user ID** — add the user's ID to the `queryKey` for every user-specific query (`['leagues', userId]`, `['roster', slug, userId]`, etc.) so that even if the cache is not cleared, data from a different user ID is treated as a cache miss.

## Out of Scope

- Backend changes (already filtering correctly)
- Persisting the query cache across page reloads
