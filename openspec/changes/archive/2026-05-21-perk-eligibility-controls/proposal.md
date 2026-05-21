# Proposal: Perk Eligibility Controls

## What

Enforce time-bounded eligibility windows on both league perks:

- **Swap**: usable only in the post-draft, pre-merge window — after picks lock and before the tribes consolidate into one.
- **Boost**: usable only on future, unscored episodes, and explicitly blocked on the finale.

## Why

Currently both perks have minimal enforcement. The swap has a draft-lock check but no upper bound, meaning a player could theoretically swap a castaway after the merge (when the strategic value has fundamentally changed). The boost has no finale restriction, allowing it to be saved for the finale where it would have an outsized guaranteed impact.

These controls make the game mechanics faithful to how Survivor actually works:

1. **Swap window = pre-merge**: Tribes merging is the single biggest structural event each season. Allowing swaps after the merge removes the strategic pressure that makes the perk interesting — you'd be able to dump an eliminated player reactively rather than making a forward-looking prediction.
2. **Boost excludes the finale**: The finale is a special episode with no standard tribal council. Allowing boost on it would let players trivially maximize points on the most point-rich episode. Excluding it keeps the perk about mid-game strategy.

## Goals

- Swap perk is rejected server-side if the merge episode has already aired.
- Boost perk is rejected server-side if the target episode is the season finale.
- Both the `Episode.is_merge` and `Episode.is_finale` flags are populated automatically during the season data sync.
- The frontend reflects eligibility state: swap UI indicates when the window has closed; boost UI only presents eligible episodes.
- Clear, human-readable error messages when a perk is used outside its window.

## Non-Goals

- No retroactive invalidation of perks already used.
- No admin override to re-open a closed perk window (owners cannot extend the swap window past the merge).
- No change to boost multiplier, scoring logic, or swap mechanics themselves — only eligibility gating.

## Success Criteria

- A swap attempted after the merge episode airs returns a 400 with a clear message.
- A boost targeted at the finale returns a 400 with a clear message.
- After sync, `Episode.is_merge` and `Episode.is_finale` are correctly set from the survivoR dataset.
- The Roster page shows a "window closed" state for the swap after the merge and presents only eligible episodes for the boost picker.
