# Proposal: Season Lifecycle Management

## Problems

### Bug 1 — Wrong season shown on "How to Play"
`_sync_season` sets `is_active=True` on every season it syncs but never deactivates the previous one. With two active seasons in the DB, `Season.objects.filter(is_active=True).first()` returns the lowest season number (47 instead of 50) due to the default ordering. Every view that uses `is_active` is silently broken after a new season is synced.

### Bug 2 — `ACTIVE_SEASON` hardcoded in AdminPage
`const ACTIVE_SEASON = 50` on line 168 of `AdminPage.tsx` means the admin scoring panel targets the wrong season whenever season number changes. It should be driven by the active season API.

## Feature — Season lifecycle

When a Survivor season finishes and a new one begins, the current flow has no concept of "this league is over." Leagues remain active indefinitely, and old scoring data is mixed with new. The desired lifecycle is:

1. **In-flight**: league is open for drafting, scoring runs automatically each episode.
2. **Concluded**: draft is closed, final scores are locked, data is read-only but still fully viewable.
3. **Archived**: triggered manually by the admin when a new season starts. All leagues for the old season are locked and surfaced as "past seasons" to players.

## What

1. **Fix sync task** — when syncing season N, deactivate all other US seasons so exactly one `is_active=True` season exists at all times.
2. **Fix AdminPage** — replace the hardcoded constant with a dynamic value from the existing `useActiveSeason()` hook.
3. **Add `is_archived` to `League`** — new boolean field; archived leagues are fully read-only.
4. **Backend enforcement** — draft saves, swap, and boost return 403 on archived leagues.
5. **Admin "Archive Season" action** — one-click action in the admin panel: closes all league drafts and marks all leagues for a season as archived.
6. **Dashboard** — split "My Leagues" into active leagues and a collapsible "Past Seasons" section.
7. **LeaguePage** — show an "Archived" badge and hide the Draft/My Roster action buttons for archived leagues.

## Scope

- Backend: `League` model migration, sync task fix, three view guards, new admin endpoint
- Frontend: AdminPage dynamic season, dashboard split, league page badge
- No data deleted — all rosters, scores, and history remain accessible
