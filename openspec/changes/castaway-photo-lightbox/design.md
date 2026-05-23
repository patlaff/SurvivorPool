# Design: Castaway Photo Lightbox

## State

A single `useState` at the `DraftPage` level holds the currently-zoomed castaway (or `null`):

```typescript
const [zoomedCastaway, setZoomedCastaway] = useState<Castaway | null>(null)
```

No prop drilling needed — the lightbox component and the image click handler both live in the same file.

## Image click handler

The castaway image is currently inside a `<button>` that handles pick toggling. The click on the image must **stop propagation** so the card isn't also toggled:

```typescript
// Inside the card map:
<div
  onClick={e => { e.stopPropagation(); setZoomedCastaway(c) }}
  className="cursor-zoom-in relative group/photo flex-shrink-0"
>
  <img
    src={c.image_url}
    alt={c.name}
    referrerPolicy="no-referrer"
    className="w-14 h-14 rounded-full object-cover object-top"
  />
  {/* Hover affordance — magnifier icon overlay */}
  <div className="absolute inset-0 rounded-full bg-black/30 flex items-center justify-center
                  opacity-0 group-hover/photo:opacity-100 transition-opacity pointer-events-none">
    <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-white" fill="none"
         viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
            d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0zm-6-3v6m-3-3h6" />
    </svg>
  </div>
</div>
```

The `pointer-events-none` on the overlay div ensures only the wrapping `<div>` receives the click.

## Lightbox component

A `CastawayLightbox` component rendered at the bottom of `DraftPage`'s JSX:

```typescript
function CastawayLightbox({
  castaway,
  onClose,
}: {
  castaway: Castaway
  onClose: () => void
}) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      {/* Modal panel — stopPropagation so clicking inside doesn't close */}
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-6 max-w-xs w-full flex flex-col items-center gap-4"
        onClick={e => e.stopPropagation()}
      >
        {castaway.image_url ? (
          <img
            src={castaway.image_url}
            alt={castaway.name}
            referrerPolicy="no-referrer"
            className="w-48 h-48 rounded-full object-cover object-top ring-4 ring-survivor-orange"
          />
        ) : (
          <div className="w-48 h-48 rounded-full bg-gray-200 dark:bg-gray-700
                          flex items-center justify-center text-gray-400 text-5xl">?</div>
        )}
        <div className="text-center">
          <h2 className="text-lg font-bold">{castaway.display_name ?? castaway.name}</h2>
          {castaway.age && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Age {castaway.age}{castaway.hometown ? ` · ${castaway.hometown}` : ''}
            </p>
          )}
          {castaway.occupation && (
            <p className="text-xs text-gray-400 dark:text-gray-500">{castaway.occupation}</p>
          )}
          {castaway.original_tribe && (
            <span
              className="inline-block mt-2 text-xs font-medium px-3 py-1 rounded-full text-white"
              style={{ backgroundColor: castaway.tribe_color || '#888' }}
            >
              {castaway.original_tribe}
            </span>
          )}
          {castaway.is_eliminated && (
            <p className="text-xs text-red-500 mt-1">Eliminated Ep {castaway.eliminated_episode}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 mt-1"
        >
          Close
        </button>
      </div>
    </div>
  )
}
```

## Wiring in DraftPage

```tsx
// At bottom of DraftPage return:
{zoomedCastaway && (
  <CastawayLightbox
    castaway={zoomedCastaway}
    onClose={() => setZoomedCastaway(null)}
  />
)}
```

## Fallback for no-image castaways

The `?` placeholder still gets the zoom wrapper and magnifier overlay. Tapping it opens the lightbox with the `?` placeholder at 192px, which at least shows the name/details clearly. Acceptable edge case — these castaways will have images once an alias is set and the image is re-fetched.

## Dark mode

The modal uses `.dark:bg-gray-800` and dark text variants, consistent with the rest of the app.

## Files changed

| File | Change |
|------|--------|
| `frontend/src/pages/DraftPage.tsx` | Add `zoomedCastaway` state, zoom wrapper + overlay on image, `CastawayLightbox` component, render lightbox when state is non-null |

No backend changes. No new dependencies.
