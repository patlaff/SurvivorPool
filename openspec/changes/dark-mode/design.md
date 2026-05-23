# Design: Dark Mode

## Architecture

### Strategy: Tailwind `class` dark mode

Add `darkMode: 'class'` to `tailwind.config.js`. Tailwind will apply `dark:` variants only when the `dark` class is present on `<html>`. No CSS variables or separate stylesheets needed.

### Persistence hook: `useDarkMode`

New file: `frontend/src/hooks/useDarkMode.ts`

```typescript
import { useEffect, useState } from 'react'

export function useDarkMode() {
  const [dark, setDark] = useState<boolean>(() => {
    const stored = localStorage.getItem('dark-mode')
    if (stored !== null) return stored === 'true'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('dark-mode', String(dark))
  }, [dark])

  return { dark, toggle: () => setDark(d => !d) }
}
```

- Initializes from `localStorage` key `"dark-mode"`.
- Falls back to `prefers-color-scheme` when no stored preference exists.
- Effect syncs `<html>` class and persists preference on every change.

### Toggle button in `Layout.tsx`

Import `useDarkMode` and render a Sun/Moon button immediately before the "Sign out" button:

```tsx
const { dark, toggle } = useDarkMode()

// Inside the user actions flex row, before Sign out:
<button
  onClick={toggle}
  aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
  className="text-gray-400 hover:text-white transition-colors"
  title={dark ? 'Light mode' : 'Dark mode'}
>
  {dark ? (
    // Sun icon (you're in dark mode, click to go light)
    <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364-.707.707M6.343 17.657l-.707.707M17.657 17.657l.707.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
    </svg>
  ) : (
    // Moon icon (you're in light mode, click to go dark)
    <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
    </svg>
  )}
</button>
```

The nav background is `bg-survivor-dark` (`#1A1A2E`) — already dark — so the toggle button sits on a dark surface regardless of mode. No special dark-mode styling needed for the header itself.

## Dark-mode colour mappings

### `index.css` component classes

Each shared component class needs dark variants added to its `@apply`:

| Class | Light | Dark additions |
|-------|-------|----------------|
| `body` | `bg-gray-50 text-gray-900` | `dark:bg-gray-900 dark:text-gray-100` |
| `.card` | `bg-white border-gray-200` | `dark:bg-gray-800 dark:border-gray-700` |
| `.btn-secondary` | `bg-white text-gray-700 border-gray-300 hover:bg-gray-50` | `dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-600` |
| `.input` | `border-gray-300 text-gray-900 placeholder-gray-400` | `dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500` |
| `.label` | `text-gray-700` | `dark:text-gray-300` |
| `.badge-gray` | `bg-gray-100 text-gray-600` | `dark:bg-gray-700 dark:text-gray-300` |
| `.badge-green` | `bg-green-100 text-green-800` | `dark:bg-green-900 dark:text-green-200` |
| `.badge-red` | `bg-red-100 text-red-800` | `dark:bg-red-900 dark:text-red-200` |

### Inline utility classes in pages

Pages use inline Tailwind classes for table rows, dividers, and supplementary text. Key mappings:

| Light class | Dark addition |
|-------------|---------------|
| `bg-gray-50` (table headers / page bg) | `dark:bg-gray-700` or `dark:bg-gray-800` |
| `text-gray-500` | `dark:text-gray-400` |
| `text-gray-400` | `dark:text-gray-500` |
| `text-gray-700` | `dark:text-gray-300` |
| `text-gray-600` | `dark:text-gray-400` |
| `text-gray-900` | `dark:text-gray-100` |
| `border-gray-100` | `dark:border-gray-700` |
| `border-gray-200` | `dark:border-gray-700` |
| `divide-gray-100` | `dark:divide-gray-700` |
| `divide-gray-200` | `dark:divide-gray-700` |

## Files to change

1. `frontend/tailwind.config.js` — add `darkMode: 'class'`
2. `frontend/src/hooks/useDarkMode.ts` — new file
3. `frontend/src/components/Layout.tsx` — import hook, add toggle button
4. `frontend/src/index.css` — dark variants on all component classes + body
5. `frontend/src/pages/DashboardPage.tsx` — dark variants on inline classes
6. `frontend/src/pages/LeaguePage.tsx` — dark variants on inline classes
7. `frontend/src/pages/DraftPage.tsx` — dark variants on inline classes
8. `frontend/src/pages/RosterPage.tsx` — dark variants on inline classes
9. `frontend/src/pages/RosterViewPage.tsx` — dark variants on inline classes
10. `frontend/src/pages/AdminPage.tsx` — dark variants on inline classes
11. `frontend/src/pages/InfoPage.tsx` — dark variants on inline classes
12. `frontend/src/pages/CreateLeaguePage.tsx` — dark variants on inline classes
13. Frontend rebuild + redeploy

## Non-goals

- Animated transition between modes (can be added later with a CSS `transition` on `body`).
- Separate dark SVG assets or illustrations.
- Dark mode for the login page (it has a fixed gradient header; light body looks fine).
