# Tasks: Navigation Improvements

## Task 1 — Update header: logo link + "My Leagues" nav link

**File:** `frontend/src/components/Layout.tsx`

- [x] Change the `🔥 SurvivorPool` `<Link>` target from `to="/"` to `to="/info"`
- [x] Add a `<Link to="/">My Leagues</Link>` nav item immediately before the existing `How to Play` link (same styling: `text-sm text-gray-300 hover:text-white transition-colors`)

Test: Header shows `My Leagues` and `How to Play` links; clicking the flame logo navigates to `/info`; clicking `My Leagues` navigates to `/`.

---

## Task 2 — Create reusable `Breadcrumbs` component

**File:** `frontend/src/components/Breadcrumbs.tsx` _(new file)_

- [x] Create the component with a `crumbs: { label: string; to?: string }[]` prop
- [x] Render crumbs separated by `›`; crumbs with `to` are `<Link>`, the last crumb (no `to`) is plain text
- [x] Style: `text-sm text-gray-400 mb-4`; links use `hover:text-gray-700 transition-colors`

Test: Renders correctly with and without links; last crumb is never a link.

---

## Task 3 — Add breadcrumbs to `DraftPage`

**File:** `frontend/src/pages/DraftPage.tsx`

- [x] Import `Breadcrumbs` from `../components/Breadcrumbs`
- [x] Render `<Breadcrumbs>` as the very first element inside the page `<div>`, before the `h1`:
  ```
  My Leagues › [league.name] › Draft
  ```
  where `[league.name]` links to `/leagues/${slug}` and `Draft` is plain text.

Test: Breadcrumbs appear above "Draft — League Name" heading; clicking league name navigates to the league page; clicking `My Leagues` navigates to `/`.

---

## Task 4 — Add breadcrumbs to `RosterPage`

**File:** `frontend/src/pages/RosterPage.tsx`

- [x] Import `Breadcrumbs`
- [x] Import `useLeague` from `../api/leagues` and `useAuth` from `../hooks/useAuth` if not already present
- [x] Fetch `league` with `useLeague(slug!, user?.id)`
- [x] Render breadcrumbs above the page heading:
  ```
  My Leagues › [league.name] › My Roster
  ```

Test: Same as Task 3, last crumb reads "My Roster".

---

## Task 5 — Add breadcrumbs to `RosterViewPage`

**File:** `frontend/src/pages/RosterViewPage.tsx`

- [x] Import `Breadcrumbs`, `useLeague`, and `useAuth`
- [x] Add `useAuth()` and `useLeague(slug!, user?.id)` calls
- [x] Render breadcrumbs above the player avatar/heading block:
  ```
  My Leagues › [league.name] › [Player Name]'s Roster
  ```
  where player name comes from `roster?.user.display_name`.

Test: Breadcrumbs show correct league name and player name; works while roster is loading (shows `…` placeholders).

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — Header links | — |
| 2 — Breadcrumbs component | — |
| 3 — DraftPage breadcrumbs | 2 |
| 4 — RosterPage breadcrumbs | 2 |
| 5 — RosterViewPage breadcrumbs | 2 |
