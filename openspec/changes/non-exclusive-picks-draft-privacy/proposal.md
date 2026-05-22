# Proposal: Non-Exclusive Picks & Draft Privacy

## What

Two related rule changes that correct how the draft works:

### 1 — Remove pick exclusivity
Castaways are **not exclusive**. Multiple players in the same league can pick the same castaway. Two players can have identical rosters. The current server-side "already drafted by another player" guard must be removed, and the `AvailableCastawaysView` endpoint should return all season castaways (not filtered by what others have picked).

### 2 — Hide rosters during the draft window
While the draft window is **open**, a player may only see **their own** roster. All other players' rosters are hidden — visiting a league member's roster page, viewing the leaderboard rows, or any other roster-revealing surface should be blocked until the draft closes. Once the draft window **closes**, all rosters become visible as normal.

---

## Why

The current implementation was built on an incorrect assumption that each castaway can only appear on one roster per league. Survivor Pool is designed so every player independently picks their own team; two players rooting for the same castaway is a perfectly valid (if risky) strategy.

Hiding rosters during the draft prevents strategic copying: if Player A can see Player B's five picks in real time, they might simply mirror them. Keeping picks private until the window closes preserves the integrity of independent drafting.

---

## Scope

**In scope:**
- Remove the "already drafted by another player" check in `DraftView.put`
- Remove the castaway-exclusion filter from `AvailableCastawaysView`
- Block access to other players' rosters (via `RosterView`, leaderboard entries, `ActivityLogView`) while the draft is open
- Leaderboard: hide individual roster composition and episode-score breakdown rows while draft is open; total points can remain visible (or be hidden too — see Design)
- Own roster page: always visible to the roster owner regardless of draft state

**Out of scope:**
- Changing scoring logic
- Changing how perks are applied
- Changing draft window controls (owner already has those)
