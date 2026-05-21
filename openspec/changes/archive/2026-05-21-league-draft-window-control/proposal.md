# Proposal: League Draft Window Control

## What

Give league owners manual control over their league's draft window — the ability to open or close drafting immediately, and to schedule an exact datetime when the draft will automatically close. This is a per-league setting that overrides the global season-level draft lock date.

## Why

The current draft window is driven entirely by the survivoR data sync: it closes automatically on the air date of Episode 2, derived from the `Season.draft_lock_date` field. This creates two problems:

1. **No flexibility for league owners.** If a league starts mid-season, the owner has no way to open a draft window at all. If players need more time, there's no grace period mechanism.
2. **No scheduling.** Owners can't say "close drafts at 8 PM the night before the premiere" — the granularity is a calendar date, not a time.

League owners run private pools with their own groups of friends and need the same control they'd have running a paper pool — they should be able to open, close, and schedule the window on their own terms.

## Goals

- League owners can close their league's draft window immediately from the UI.
- League owners can reopen a closed draft window (e.g., for a grace period).
- League owners can set a specific future datetime for the draft to auto-close.
- All draft window state is per-league, not per-season.
- Non-owners see the draft window status but have no controls.
- The existing season-level `draft_lock_date` still acts as the default when no per-league override is set.

## Non-Goals

- This does not replace the automatic season sync / Episode 2 lock logic — `Season.draft_lock_date` remains the default when no per-league override is set, but league owners can always override it in either direction.
- This is not a global admin tool; it is strictly a league owner self-service feature.
- No email/push notifications when the draft closes.

## Success Criteria

- A league owner can click "Close draft now" and immediately prevent any further pick changes in their league.
- A league owner can set a scheduled close datetime; the UI shows a live countdown and the draft locks at that time without any manual action.
- A league owner can reopen a draft that was manually closed (as long as the season lock date has not passed).
- The draft window UI for non-owners accurately reflects whether the draft is open or closed.
