# Proposal: Join & Boost Cleanup

## What

Two small UX/correctness fixes:

1. **Remove slug from Join League form** — the "League URL Slug" input should not be visible to users. An invite code alone should be enough to join a league; forcing users to also know the URL slug is confusing and redundant.

2. **Boost eligibility: aired episodes** — the Boost perk should only be usable on episodes that haven't aired yet (future episodes). Currently, the guard only checks that the episode hasn't been *scored*, but a scoring delay means an aired-but-unscored episode would incorrectly appear as eligible.

## Why

- The slug is an implementation detail. Users share invite codes, not slugs. Asking for both creates friction and confusion.
- Boost is strategically meaningful only when applied before an episode airs — applying it after the fact (even if scoring is delayed) contradicts the intended game mechanic.

## Out of scope

- Redesigning the join flow beyond removing the slug field
- Other perk eligibility changes
