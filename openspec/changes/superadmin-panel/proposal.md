# Proposal: Superadmin Panel

## What

A superadmin panel accessible only to a configurable list of email addresses (default: `patlaff728@gmail.com`). The panel provides four capabilities:

1. **League oversight** — view all leagues across all users (name, owner, member count, test flag, draft status).

2. **Test leagues** — create leagues with relaxed restrictions: no draft window enforcement, eliminated castaways can be drafted, the "already taken by another roster" guard is lifted, and perk window/air-date restrictions are bypassed. Test leagues are flagged visually so they're easy to distinguish.

3. **Season scoring summary** — see all scored episodes for a season, with a full per-castaway event breakdown and per-episode totals. Provides confidence that the scoring pipeline is computing correctly.

4. **Scoring config editor** — view and edit the key→point mappings in `scoring_config.json` via a simple UI. After saving, offer a "Re-score all episodes" action that recomputes all `ScoringEvent.points`, `PlayerEpisodeScore.raw_points`, and `PlayerEpisodeScore.final_points` using the new values — without re-fetching survivoR data.

## Why

- Point values will need tuning during the season. An in-app editor is faster than shelling into the container to edit JSON.
- Re-scoring must be available so any config change is immediately reflected in the leaderboard.
- Test leagues let the admin verify the full draft + perk + scoring flow without polluting real league data.
- The season scoring summary gives an at-a-glance audit trail for every castaway event that has been detected and scored.

## Out of scope

- User management (banning, resetting accounts)
- Retroactively editing individual `ScoringEvent` rows via the UI (Django admin already handles that)
- Multi-season superadmin support beyond the active season
