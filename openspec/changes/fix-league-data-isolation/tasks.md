# Tasks: Fix League Data Isolation

## Task 1 — Clear query cache on logout

**File:** `frontend/src/hooks/useAuth.ts`

- [x] Import `useQueryClient` from `@tanstack/react-query`
- [x] Add `const queryClient = useQueryClient()` inside `useAuth()`
- [x] Add `queryClient.clear()` as the first line of the `logout` callback (before `clearTokens()`)
- [x] Add `queryClient` to the `useCallback` dependency array for `logout`

Expected result: logging out then back in as a different user never shows stale data from the previous session.

Test:
1. Log in as User A → visit dashboard → note leagues shown
2. Log out → log in as User B (no league memberships) → dashboard must show empty state immediately, not A's leagues

---

## Task 2 — User-scope user-specific query keys

**File:** `frontend/src/api/leagues.ts`

Add a `userId?: number` parameter to each user-specific hook and include it in the query key. Also add `enabled: !!userId` to skip the fetch before the user is known.

Hooks to update:

- [x] `useMyLeagues(userId?: number)` → key `['leagues', userId]`, `enabled: !!userId`
- [x] `useLeague(slug, userId?: number)` → key `['league', slug, userId]`, `enabled: !!userId`
- [x] `useDraft(slug, userId?: number)` → key `['draft', slug, userId]`, `enabled: !!userId`
- [x] `useMyRoster(slug, userId?: number)` → key `['roster', slug, 'me', userId]`, `enabled: !!userId`

Note: `useLeaderboard`, `useSeasonCastaways`, `useSeasonEpisodes`, and `useAvailableCastaways` return data that is either the same for all league members or requires no user scoping — leave them unchanged.

Test: After the change, TypeScript must compile cleanly. Existing `invalidateQueries({ queryKey: ['leagues'] })` calls in mutation `onSuccess` handlers do NOT need updating — TanStack Query's prefix matching will still invalidate `['leagues', userId]`.

---

## Task 3 — Pass userId in DashboardPage

**File:** `frontend/src/pages/DashboardPage.tsx`

- [x] Import `useAuth` from `../hooks/useAuth`
- [x] Add `const { user } = useAuth()` inside the component
- [x] Change `useMyLeagues()` → `useMyLeagues(user?.id)`

Test: With no user (logged out), the query is disabled and no request is made. With a user, only their leagues appear.

---

## Task 4 — Pass userId in DraftPage

**File:** `frontend/src/pages/DraftPage.tsx`

- [x] Import `useAuth` from `../hooks/useAuth`
- [x] Add `const { user } = useAuth()` inside the component
- [x] Change `useLeague(slug!)` → `useLeague(slug!, user?.id)`
- [x] Change `useDraft(slug!)` → `useDraft(slug!, user?.id)`

---

## Task 5 — Pass userId in RosterPage

**File:** `frontend/src/pages/RosterPage.tsx`

- [x] Import `useAuth` from `../hooks/useAuth` (if not already imported)
- [x] Add `const { user } = useAuth()` inside the component
- [x] Change `useLeague(slug!)` → `useLeague(slug!, user?.id)`
- [x] Change `useMyRoster(slug!)` → `useMyRoster(slug!, user?.id)`

---

## Task 6 — Pass userId in LeaguePage

**File:** `frontend/src/pages/LeaguePage.tsx`

`useAuth` is already imported and `user` is already destructured.

- [x] Change `useLeague(slug!)` → `useLeague(slug!, user?.id)`

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — Clear cache on logout | — |
| 2 — User-scope query keys | — |
| 3 — DashboardPage | 2 |
| 4 — DraftPage | 2 |
| 5 — RosterPage | 2 |
| 6 — LeaguePage | 2 |

Tasks 1 and 2 are independent and can be done simultaneously. Tasks 3–6 depend on Task 2 signature changes.
