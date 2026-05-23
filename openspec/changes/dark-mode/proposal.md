# Proposal: Dark Mode

## What

Add a persistent dark mode to the SurvivorPool frontend, toggled by a Sun/Moon icon button in the top navigation bar to the left of the "Sign Out" button.

## Why

Users browsing the site in low-light environments (evening draft sessions, late-night episode scoring) get eye strain from the bright white layout. A dark mode follows modern web app conventions and improves comfort during extended use.

## Scope

- **Toggle button** in the header: Sun icon (light mode active) or Moon icon (dark mode active), placed immediately left of "Sign Out".
- **Persistence**: preference saved to `localStorage` so it survives page refreshes and re-visits. Falls back to `prefers-color-scheme` on first visit (no stored preference).
- **Strategy**: Tailwind `darkMode: 'class'` — a `dark` class is toggled on `<html>`. No CSS variables; pure Tailwind dark utility classes.
- **Coverage**: all pages visible to regular users and the admin panel.

## Out of Scope

- Per-league or per-user server-side preference storage.
- Separate dark-mode color palette / theme tokens (use standard Tailwind dark variants).
- Email notification templates (always rendered in light context by mail clients).
