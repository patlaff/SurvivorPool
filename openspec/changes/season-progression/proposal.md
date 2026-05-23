# Proposal: Season Progression

## Problems

### Bug — `ACTIVE_SEASON` env var is a manual, fragile source of truth

`sync_season_data` reads `settings.ACTIVE_SEASON` (an `.env` integer) to know which season to sync each day. This means:
- The env var and `Season.is_active` DB flag are two independent sources of truth that can drift.
- Moving to a new season requires a deployment-time env change + container restart — a manual ops step that is easy to forget or mistime.
- There is no mechanism to detect when the next season's data has appeared in the upstream dataset.

## Feature — Automated season progression with superadmin notifications

When a Survivor season ends and a new one begins ~4 months later, the current site has no automated path forward. The desired flow is:

1. **Dormant period**: After leagues are archived, celery still runs daily. The sync keeps the active season's data fresh, and a new probe checks whether the *next* season's castaways have appeared in the `doehm/survivoR` dataset.
2. **First detection email**: The moment any castaway data for S+1 appears, email all superadmins: "Season N+1 data has appeared — N castaways found."
3. **Completeness email**: Once ≥ 18 castaways are present (full cast announced), email again: "Season N+1 cast looks complete." If the admin progresses before this threshold is reached, the completeness email is suppressed.
4. **"Progress" action**: A single admin button atomically archives the current season's leagues, deactivates the current season, syncs the next season's data, and activates it — no env var changes, no container restarts.

## What

1. **DB-driven sync** — Remove `settings.ACTIVE_SEASON` from `sync_season_data`. Read the active season from the DB instead. The env var becomes a bootstrap-only artifact (documented in `.env.example`).
2. **Next-season probe** — Each daily sync probes for `active_season + 1` data in the survivoR dataset after syncing the current season.
3. **`Season` model additions** — Three new fields track progression state: `allows_new_leagues`, `next_detected_at`, `next_complete_notified_at`.
4. **Email notifications** — Django `send_mail` via Gmail SMTP. Two emails per season transition: detected + complete. Recipients: `settings.SUPERADMIN_EMAILS`.
5. **`AdminProgressSeasonView`** — Replaces `AdminArchiveSeasonView`. When a next season is detected, this endpoint atomically archives current leagues + syncs the new season.
6. **Admin panel widget** — Three-state UI: (1) active leagues → "Archive Season N"; (2) dormant, no next data → "Watching for Season N+1"; (3) next detected → "Progress from Season N → N+1".
7. **Dashboard** — Hide "New League" button when `season.allows_new_leagues` is false.

## Scope

- Backend: `Season` migration, revised sync task, probe helper, email utility, new admin endpoint
- Frontend: Admin panel widget, dashboard guard
- No data deleted — all history remains accessible
- Gmail SMTP credentials added to `.env` (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` app password)
