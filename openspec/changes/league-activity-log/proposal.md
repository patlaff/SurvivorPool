# Proposal: League Activity Log

## What

Add an **Activity Log** tab to the league detail page (`/leagues/<slug>`) visible only to the league owner. The tab displays a reverse-chronological feed of player actions in the league:

- **Draft saved** — when a user first locks in their 5 picks, and again each time they re-save before the draft closes. Shows the castaway names at each save.
- **Swap used** — when a user activates their Swap perk. Shows the dropped castaway and the added castaway.
- **Boost used** — when a user activates their Boost perk. Shows which episode they doubled points for.

## Why

League owners currently have no visibility into player behaviour within their league. An activity log gives the owner:
- Confirmation that all players have drafted on time
- A record of perk usage (useful for dispute resolution)
- A timeline of how the roster composition has changed over the season

## Data availability

Swap and Boost events are **already fully tracked** — `Perk.used_at`, `Perk.swapped_out_castaway`, `Perk.swapped_in_castaway`, and `Perk.boost_target_episode` capture everything needed.

Draft events are **not fully tracked**. `DraftView.put` deletes all `RosterSlot` rows and recreates them on each save, so only the timestamp of the *last* save survives. To capture the full draft history (including re-saves), a new `DraftSave` audit model is required.

## Out of Scope

- Activity visible to non-owner members
- Push notifications or real-time updates
- Edit or delete activity log entries
