# Proposal: Navigation Improvements

## What

Three small navigation enhancements to the header and league sub-pages:

1. **Add a "My Leagues" link to the header** — an explicit link back to the dashboard (`/`) so users can jump back to their league list from anywhere without having to click the logo.
2. **Re-purpose the `🔥 SurvivorPool` logo link** — change it from linking to `/` to linking to `/info` (How to Play), while keeping the existing "How to Play" text link in the nav as-is.
3. **Add breadcrumbs to league sub-pages** — the Draft and My Roster pages (and the Roster View page) currently show no indication of which league they belong to, and there's no one-click path back to the main league page. Breadcrumbs in the form `My Leagues › [League Name] › [Page]` fix this.

## Why

- Users navigating to `/leagues/:slug/draft` or `/leagues/:slug/roster` have no visible path home. The only option is the browser back button or editing the URL.
- The logo click-target is unintuitive — the flame icon feels like a brand/home link, but "home" for a logged-in user is their league list, and the logo re-directing to `/info` gives it a clearer identity (the brand tells you how to play).
- A "My Leagues" label in the nav makes the primary destination explicit and scannable.

## Scope

Frontend only — no backend changes required. All changes are in `Layout.tsx` and the three sub-page components (`DraftPage`, `RosterPage`, `RosterViewPage`).
