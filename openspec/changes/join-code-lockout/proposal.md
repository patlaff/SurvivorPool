# Proposal: Join Code Brute-Force Lockout

## What

Track failed join-code attempts per authenticated user. After 5 consecutive failures, enforce a logarithmically increasing cooldown before the user can try again. Successful joins reset the counter.

## Why

League invite codes are 8-character uppercase alphanumeric strings (~2.8 trillion combinations), but shorter or predictable codes could still be targeted. More practically, a logged-in bot or malicious user could write a script that hammers the join endpoint in an attempt to stumble into an active league. This feature adds a low-friction speed-bump: normal users who mistype a code a couple of times are unaffected, but systematic attempts slow to a crawl.

## Scope

- **Backend only for the core logic** — a small Redis-backed helper module + one view change
- **Frontend UX** — surface the `retry_after` value from the 429 response so the user sees a human-readable message instead of a generic error
- **Keyed per authenticated user** — the join endpoint already requires authentication (`IsAuthenticated`), so `user.id` is the lockout key; no IP tracking needed
- **Logarithmic growth, not exponential** — delays grow slowly on purpose (30 s → 60 s → 90 s → …), matching the low-stakes nature of the app while still defeating scripted attacks

## Out of Scope

- Locking out the account entirely (a cooldown is sufficient)
- Admin UI to view or clear lockout state (Redis TTLs handle cleanup automatically)
- Extending lockout to any other endpoint
