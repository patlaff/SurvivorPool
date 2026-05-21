# Proposal: Survivor Fantasy Web App

## Summary

Build a full-stack web application that lets players compete in private Survivor fantasy leagues. Players draft five castaways at the start of each season, earn points automatically after every episode based on in-game events, use one-time perks to change strategy mid-season, and track standings on a live leaderboard — all without any manual intervention from a league admin.

## Problem

Survivor fantasy pools are typically run via spreadsheets or group chats, requiring a dedicated admin to watch every episode, manually log events, calculate points, and post standings. This is tedious, error-prone, and doesn't scale to multiple leagues. Players have no self-service visibility into how their points were earned.

## Goals

- **Zero-friction login**: Authentication is delegated entirely to Google. No passwords to manage. Users sign in with their Google/Gmail account; the app stores only their display name, email, and avatar.
- **Automated scoring**: Points are calculated from structured episode data (survivoR2py) and written to the database automatically after each episode airs, with no human action required.
- **Self-service draft**: Players log in, join a league, and draft castaways themselves. Picks can be revised freely until the start of the second episode of the season, at which point rosters lock automatically for the entire league. During the draft window, players can view all upcoming castaways to research and plan picks.
- **Perks system**: Each player gets one Swap (replace a castaway once per season) and one Boost (double their points for one episode), usable at will through the UI after the draft locks.
- **Live leaderboard**: Per-episode and cumulative standings — including other players' rosters — visible to all league members.
- **Multiple leagues**: A single instance supports many independent leagues. Players can belong to more than one league.
- **Configurable scoring**: Point values live in `scoring_config.json` so the league owner can adjust them without touching code.
- **US seasons only**: All data fetching, filtering, and display is scoped to US versions of Survivor.

## Non-Goals

- Password-based authentication or any self-managed credential system.
- Real-money or prize pool management.
- Mobile native app (responsive web is sufficient).
- Live real-time updates during an episode (post-episode daily sync is enough).
- Scoring events with no programmatic source in survivoR2py (see Scoring section in design.md for the complete exclusion list).
- Social features beyond the league leaderboard (chat, emoji reactions, etc.).
- Non-US Survivor seasons.

## Permissions Model

All authenticated users in a league can:
- View the league leaderboard (all players, all scores).
- View the castaway picks of any other player in the league.
- View the scoring event log for any roster in the league.

Users can only modify:
- Their own roster (draft picks, swap, boost).
- Their own league membership (join / leave).

League owners additionally can:
- Edit the league name.
- Remove members.

No user can modify another player's draft picks, perks, or any league settings they do not own.

## Draft Window

At the start of each US season, a Draft module opens for all players enrolled in a league for that season. Players may:
1. Browse upcoming castaway information (name, age, hometown, occupation, and any available bio).
2. Select and save their 5 castaways — changes are allowed at any time during the draft window.

The draft window closes automatically when Episode 2 of the season airs. At that moment, all rosters in all leagues for that season lock simultaneously. No further pick changes are permitted for the rest of the season (only Swap/Boost perks remain available).

## Success Criteria

1. After an episode airs, the Celery Beat task runs at 21:05 PT and writes `PlayerEpisodeScore` rows for all active leagues with zero manual steps.
2. A new player can sign in with Google, join a league, complete a draft of 5 castaways, and see their roster — all within 5 minutes.
3. The leaderboard refreshes to reflect new scores within minutes of the scoring task completing.
4. A league owner can adjust point values in `scoring_config.json` and have them take effect on the next scoring run.
5. The app deploys with a single `docker compose up` command.

## Stakeholders

- **League owner / admin**: Sets up leagues, adjusts scoring config, monitors the scoring pipeline.
- **Players**: Draft castaways, use perks, track standings.

## Rough Scope

Full greenfield build: backend API, database schema, scoring pipeline, and React frontend. Estimated as a multi-week solo project broken into phases (foundation → scoring → draft/perks → frontend → hardening).
