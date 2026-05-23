# Proposal: Tribe Info on Castaways

## What

Surface each castaway's original tribe — name and color — throughout the app:

1. **Backend**: Store `original_tribe` (name string) and `tribe_color` (hex string, e.g. `#ff4148`) on each `Castaway` record, populated from the survivoR dataset during season sync.
2. **Draft page**: Show a small color-coded tribe badge on each castaway card so players can identify tribe composition while making picks.
3. **Picks grid** (league page): Color-code each castaway's name by their tribe color so tribe distribution across rosters is immediately visible.

## Why

- Tribe membership is a significant strategic factor in Survivor — knowing which castaway started on which tribe helps players make better draft decisions.
- The data is already present in the survivoR dataset (`original_tribe` in `castaways.json`, hex colors in `tribe_colours.json`) — it just needs to be wired up.
- Visual color-coding makes tribe information scannable at a glance without adding noise.

## Data Source

- `castaways.json` → `original_tribe` field (e.g. `"Gata"`, `"Lavo"`, `"Tuku"`)
- `tribe_colours.json` → filtered to `tribe_status == "Original"` for the season, yields `tribe → hex color` mapping (e.g. `Gata → #fcdd31`, `Lavo → #ff4148`, `Tuku → #4cabe4`)

## Scope

- Backend: model migration + sync task update + serializer change
- Frontend: TypeScript type update + DraftPage card badge + picks grid name coloring
- No new API endpoints — tribe fields are added to the existing `CastawaySerializer`
