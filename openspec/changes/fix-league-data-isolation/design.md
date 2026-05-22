# Design: Fix League Data Isolation

## Approach

Two complementary fixes applied together: cache eviction on logout (primary), and user-scoped query keys (defense-in-depth).

---

## Fix 1 — Clear query cache on logout

**File:** `frontend/src/hooks/useAuth.ts`

Add `useQueryClient()` inside the hook and call `queryClient.clear()` from `logout`:

```ts
import { useQueryClient } from '@tanstack/react-query'

export function useAuth() {
  const queryClient = useQueryClient()
  // ...

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
    queryClient.clear()      // ← evict all cached data
  }, [queryClient])
}
```

`queryClient.clear()` removes all queries and their data from the in-memory cache. The next component that mounts after login will fetch fresh data scoped to the new user.

---

## Fix 2 — User-scoped query keys

All queries that return user-specific data should include the user ID in their `queryKey`. This ensures TanStack Query treats the same endpoint as a cache *miss* when the user changes, even before the cache is explicitly cleared.

**File:** `frontend/src/api/leagues.ts`

Every hook that returns data scoped to the authenticated user needs the user ID added to its key. The user ID is available from the decoded JWT (already stored in `useAuth`).

Because these hooks are called from components and don't have direct access to `useAuth`, the user ID must be passed in as a parameter, or the hooks can accept an optional `userId` argument with a stable fallback.

Simplest approach: pass `userId` explicitly to each user-scoped hook from the component that calls it.

### Hooks to update

| Hook | Old key | New key |
|------|---------|---------|
| `useMyLeagues` | `['leagues']` | `['leagues', userId]` |
| `useLeague(slug)` | `['league', slug]` | `['league', slug, userId]` |
| `useMyRoster(slug)` | `['roster', slug, 'me']` | `['roster', slug, userId]` |
| `useMyScores(slug)` | `['scores', slug]` | `['scores', slug, userId]` |
| `useDraft(slug)` | `['draft', slug]` | `['draft', slug, userId]` |

League-independent queries (castaways, episodes, leaderboard) are not user-specific and do not need to be scoped.

### Invalidation update

Any `qc.invalidateQueries` call that targeted the old key must be updated to match the new key. Since `userId` is not available inside the mutation hooks, the simplest fix is to use a **prefix match** (pass just the non-user portion) or switch affected mutations to accept `userId`.

Because the `queryClient.clear()` on logout already handles the cross-user case, the user-scoped keys are a secondary safety net. The invalidation strategy should remain simple: **keep `invalidateQueries` using the non-user prefix** (e.g., `{ queryKey: ['leagues'] }` still invalidates `['leagues', userId]` due to TanStack Query's prefix matching behavior).

---

## Component changes

Components that call user-scoped hooks need to pass the current `userId`. Each component already has access to `useAuth()`, so:

```ts
const { user } = useAuth()
const { data: leagues } = useMyLeagues(user?.id)
```

Hooks that currently take no arguments need a `userId` parameter added:

```ts
export function useMyLeagues(userId?: number) {
  return useQuery<League[]>({
    queryKey: ['leagues', userId],
    queryFn: () => api.get('/leagues/').then(r => r.data),
    enabled: !!userId,
  })
}
```

Adding `enabled: !!userId` ensures no fetch is attempted before the user is known (prevents a brief unauthenticated request race).

---

## Mutation invalidation

Mutations that invalidate `['leagues']` (create league, join league) will still work correctly because TanStack Query prefix-matches: `invalidateQueries({ queryKey: ['leagues'] })` invalidates ALL keys that begin with `'leagues'`, including `['leagues', userId]`.

No changes needed to mutation `onSuccess` callbacks.

---

## Summary of files changed

| File | Change |
|------|--------|
| `frontend/src/hooks/useAuth.ts` | Add `useQueryClient`, call `queryClient.clear()` in `logout` |
| `frontend/src/api/leagues.ts` | Add `userId` param + updated keys to `useMyLeagues`, `useLeague`, `useMyRoster`, `useMyScores`, `useDraft` |
| `frontend/src/pages/DashboardPage.tsx` | Pass `user?.id` to `useMyLeagues` |
| `frontend/src/pages/LeaguePage.tsx` | Pass `user?.id` to `useLeague` |
| `frontend/src/pages/DraftPage.tsx` | Pass `user?.id` to `useDraft` |
| `frontend/src/pages/RosterPage.tsx` | Pass `user?.id` to `useMyRoster`, `useMyScores` |
| `frontend/src/pages/RosterViewPage.tsx` | Pass `user?.id` to `useLeague` if used |
