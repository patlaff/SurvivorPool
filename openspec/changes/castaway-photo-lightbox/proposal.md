# Proposal: Castaway Photo Lightbox

## What

On the Draft page, tapping/clicking a castaway's profile photo opens a lightbox modal showing a larger version of the photo alongside their key details. Clicking outside the modal (or pressing Escape) closes it. Clicking the photo does **not** toggle the draft pick — that intent is reserved for the rest of the card.

## Why

Castaway photos on the draft grid are 56×56 px — small enough that it's hard to recognize returning players or distinguish between similar-looking castaways. The draft happens live during or just before an episode, often on a phone. Users want a quick way to get a better look without leaving the page or losing their draft context.

## Scope

- **Draft page only** — that's where pick decisions happen and where the need is greatest
- **All castaways** — both eliminated (faded) and active
- **Mobile-first** — touch tap opens the lightbox; keyboard Escape closes it on desktop
- A subtle `cursor-zoom-in` style and a small magnifier overlay on hover signal that the photo is tappable
- No backend changes — all frontend

## Out of Scope

- Roster page or admin castaway table (photos there are equally small, but the use case is lower-stakes)
- Swiping between castaways inside the lightbox
- Loading a higher-resolution image (we use whatever Fandom returns, already ~300 px wide)
