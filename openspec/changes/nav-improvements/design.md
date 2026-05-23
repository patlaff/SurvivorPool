# Design: Navigation Improvements

## Header changes — `frontend/src/components/Layout.tsx`

### Logo link target
Change the `🔥 SurvivorPool` anchor from `to="/"` to `to="/info"`:

```tsx
<Link to="/info" className="flex items-center gap-2 text-survivor-orange font-bold text-xl tracking-tight">
  🔥 SurvivorPool
</Link>
```

### "My Leagues" nav link
Add a `My Leagues` link immediately before `How to Play` in the authenticated nav:

```tsx
<Link to="/" className="text-sm text-gray-300 hover:text-white transition-colors">
  My Leagues
</Link>
<Link to="/info" className="text-sm text-gray-300 hover:text-white transition-colors">
  How to Play
</Link>
```

---

## Breadcrumb component — new file `frontend/src/components/Breadcrumbs.tsx`

A small reusable component that renders a `My Leagues › [League Name] › [Page]` trail:

```tsx
import { Link } from 'react-router-dom'

interface Crumb {
  label: string
  to?: string   // omit for the current (last) crumb — rendered as plain text
}

export function Breadcrumbs({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <nav className="flex items-center gap-1 text-sm text-gray-400 mb-4">
      {crumbs.map((crumb, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <span className="text-gray-300">›</span>}
          {crumb.to
            ? <Link to={crumb.to} className="hover:text-gray-700 transition-colors">{crumb.label}</Link>
            : <span className="text-gray-600">{crumb.label}</span>
          }
        </span>
      ))}
    </nav>
  )
}
```

---

## Breadcrumbs in league sub-pages

All three pages already have access to `slug` via `useParams` and `league.name` via `useLeague`.

### `DraftPage.tsx`
Add breadcrumbs above the page heading:

```tsx
import { Breadcrumbs } from '../components/Breadcrumbs'
// ...
<Breadcrumbs crumbs={[
  { label: 'My Leagues', to: '/' },
  { label: league?.name ?? '…', to: `/leagues/${slug}` },
  { label: 'Draft' },
]} />
```

### `RosterPage.tsx`
Same pattern — the existing `My Roster` heading stays; breadcrumbs go above it:

```tsx
import { Breadcrumbs } from '../components/Breadcrumbs'
// ...
<Breadcrumbs crumbs={[
  { label: 'My Leagues', to: '/' },
  { label: league?.name ?? '…', to: `/leagues/${slug}` },
  { label: 'My Roster' },
]} />
```

### `RosterViewPage.tsx`
The page shows another player's roster; the league name must be fetched:

```tsx
import { Breadcrumbs } from '../components/Breadcrumbs'
import { useLeague } from '../api/leagues'
import { useAuth } from '../hooks/useAuth'
// ...
const { user } = useAuth()
const { data: league } = useLeague(slug!, user?.id)
// ...
<Breadcrumbs crumbs={[
  { label: 'My Leagues', to: '/' },
  { label: league?.name ?? '…', to: `/leagues/${slug}` },
  { label: `${roster?.user.display_name ?? '…'}'s Roster` },
]} />
```

---

## Files changed

| File | Change |
|------|--------|
| `frontend/src/components/Layout.tsx` | Logo links to `/info`; add "My Leagues" link to `/` |
| `frontend/src/components/Breadcrumbs.tsx` | New reusable breadcrumb component |
| `frontend/src/pages/DraftPage.tsx` | Add breadcrumbs |
| `frontend/src/pages/RosterPage.tsx` | Add breadcrumbs |
| `frontend/src/pages/RosterViewPage.tsx` | Add breadcrumbs (also import `useLeague` + `useAuth`) |
