# Tasks: Castaway Photo Lightbox

## Task 1 — Add lightbox state and image click wrapper

**File:** `frontend/src/pages/DraftPage.tsx`

- [x] Add `const [zoomedCastaway, setZoomedCastaway] = useState<...| null>(null)` at the top of `DraftPage`
- [x] Wrap the castaway `<img>` (and the `?` placeholder div) in a `<div>` that:
  - Has `onClick={e => { e.stopPropagation(); setZoomedCastaway(c) }}`
  - Has `className="cursor-zoom-in relative group/photo flex-shrink-0"`
  - Removes `flex-shrink-0` from the `<img>` itself (now on the wrapper)
- [x] Add the magnifier icon overlay div inside the wrapper (see design.md)

---

## Task 2 — Add `CastawayLightbox` component

**File:** `frontend/src/pages/DraftPage.tsx`

- [x] Add `CastawayLightbox` as a module-level function component (below `DraftPage`, above the default export or at the bottom of the file)
- [x] Component receives `{ castaway, onClose }` props
- [x] Registers an `keydown` listener for Escape via `useEffect` (cleaned up on unmount)
- [x] Renders: backdrop overlay → modal panel → 192px photo → name, age/hometown, occupation, tribe badge, eliminated note → Close button
- [x] Backdrop click calls `onClose`; clicking inside the panel stops propagation
- [x] Apply dark-mode classes consistent with the rest of the file

---

## Task 3 — Render lightbox at the bottom of DraftPage

**File:** `frontend/src/pages/DraftPage.tsx`

- [x] At the end of `DraftPage`'s return JSX, add:
  ```tsx
  {zoomedCastaway && (
    <CastawayLightbox
      castaway={zoomedCastaway}
      onClose={() => setZoomedCastaway(null)}
    />
  )}
  ```
- [x] Add `useEffect` to the import line if not already importing it (needed for Escape key handler)

---

## Task 4 — Rebuild and redeploy frontend

- [x] `docker compose build frontend && docker compose up -d frontend`
- [ ] Verify: tapping a castaway photo opens the lightbox; tapping the backdrop or pressing Escape closes it; tapping the card area outside the photo still toggles the pick

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — State + image wrapper | — |
| 2 — Lightbox component | — |
| 3 — Render lightbox | 1, 2 |
| 4 — Rebuild | 3 |
