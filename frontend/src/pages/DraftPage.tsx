import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useLeague, useSeasonCastaways, useDraft, useSaveDraft, type Castaway } from '../api/leagues'
import { useAuth } from '../hooks/useAuth'
import { Breadcrumbs } from '../components/Breadcrumbs'

function useCountdown(lockDate: string | null) {
  const [remaining, setRemaining] = useState('')
  useEffect(() => {
    if (!lockDate) { setRemaining(''); return }
    const tick = () => {
      const diff = new Date(lockDate).getTime() - Date.now()
      if (diff <= 0) { setRemaining('Draft closed'); return }
      const d = Math.floor(diff / 86400000)
      const h = Math.floor((diff % 86400000) / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      setRemaining(`${d}d ${h}h ${m}m remaining`)
    }
    tick()
    const id = setInterval(tick, 60000)
    return () => clearInterval(id)
  }, [lockDate])
  return remaining
}

// ── Lightbox ──────────────────────────────────────────────────────────────────

function CastawayLightbox({ castaway, onClose }: { castaway: Castaway; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-6 max-w-xs w-full flex flex-col items-center gap-4"
        onClick={e => e.stopPropagation()}
      >
        {castaway.image_url ? (
          <img
            src={castaway.image_url}
            alt={castaway.display_name || castaway.name}
            referrerPolicy="no-referrer"
            className="w-48 h-48 rounded-full object-cover object-top ring-4 ring-survivor-orange"
          />
        ) : (
          <div className="w-48 h-48 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-400 dark:text-gray-500 text-5xl">
            ?
          </div>
        )}
        <div className="text-center">
          <h2 className="text-lg font-bold">{castaway.display_name || castaway.name}</h2>
          {castaway.age && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Age {castaway.age}{castaway.hometown ? ` · ${castaway.hometown}` : ''}
            </p>
          )}
          {castaway.occupation && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{castaway.occupation}</p>
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
            <p className="text-xs text-red-500 mt-2">Eliminated Ep {castaway.eliminated_episode}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  )
}

// ── DraftPage ─────────────────────────────────────────────────────────────────

export default function DraftPage() {
  const { slug } = useParams<{ slug: string }>()
  const { user } = useAuth()
  const { data: league } = useLeague(slug!, user?.id)
  const { data: castaways } = useSeasonCastaways(league?.season_number ?? 0)
  const { data: draft } = useDraft(slug!, user?.id)
  const saveDraft = useSaveDraft(slug!)

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState('')
  const [saved, setSaved] = useState(false)
  const [zoomedCastaway, setZoomedCastaway] = useState<Castaway | null>(null)
  const countdown = useCountdown(draft?.lock_date ?? null)

  useEffect(() => {
    if (draft?.picks) setSelected(new Set(draft.picks))
  }, [draft?.picks])

  const toggle = useCallback((id: string) => {
    if (!draft?.draft_open) return
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id); return next }
      if (next.size >= 5) return prev
      next.add(id)
      return next
    })
    setSaved(false)
  }, [draft?.draft_open])

  async function handleSave() {
    await saveDraft.mutateAsync(Array.from(selected))
    setSaved(true)
  }

  const filtered = castaways?.filter(c =>
    c.name.toLowerCase().includes(filter.toLowerCase()) ||
    c.hometown.toLowerCase().includes(filter.toLowerCase()) ||
    c.occupation.toLowerCase().includes(filter.toLowerCase())
  ) ?? []

  // Use league.draft_open as primary signal — it's invalidated/refetched by useDraftWindow
  // before the owner navigates here.  Fall back to draft.draft_open, then true while loading.
  const draftOpen = league?.draft_open ?? draft?.draft_open ?? true

  return (
    <div>
      <Breadcrumbs crumbs={[
        { label: 'My Leagues', to: '/' },
        { label: league?.name ?? '…', to: `/leagues/${slug}` },
        { label: 'Draft' },
      ]} />
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">Draft — {league?.name}</h1>
        <span className={`text-sm font-medium ${draftOpen ? 'text-green-600' : 'text-gray-400 dark:text-gray-500'}`}>
          {draftOpen ? countdown || 'Draft open' : 'Draft closed'}
        </span>
      </div>

      {!draftOpen && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-4 text-sm text-yellow-800">
          The draft has closed. Rosters are locked for the season.
        </div>
      )}

      <div className="flex items-center gap-4 mb-4">
        <input className="input flex-1" placeholder="Search by name, hometown, occupation…" value={filter} onChange={e => setFilter(e.target.value)} />
        <span className="text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">{selected.size} / 5 selected</span>
        {draftOpen && (
          <button className="btn-primary" onClick={handleSave} disabled={selected.size !== 5 || saveDraft.isPending}>
            {saved ? '✓ Saved' : 'Save Picks'}
          </button>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map(c => {
          const isSelected = selected.has(c.castaway_id)
          const isEliminated = c.is_eliminated && !league?.is_test
          return (
            <button
              key={c.castaway_id}
              onClick={() => {
                if (!draftOpen) return
                if (isEliminated && !isSelected) return
                toggle(c.castaway_id)
              }}
              className={`card text-left transition-all ${isSelected ? 'border-survivor-orange bg-orange-50 dark:bg-orange-950/30' : 'hover:border-gray-300 dark:hover:border-gray-500'} ${isEliminated && !isSelected ? 'opacity-50 cursor-not-allowed' : ''} ${!draftOpen ? 'cursor-default' : ''}`}
            >
              <div className="flex items-start gap-3">
                {/* Photo — click opens lightbox; stopPropagation prevents card toggle */}
                <div
                  className="relative group/photo flex-shrink-0 cursor-zoom-in"
                  onClick={e => { e.stopPropagation(); setZoomedCastaway(c) }}
                >
                  {c.image_url ? (
                    <img
                      src={c.image_url}
                      alt={c.display_name || c.name}
                      referrerPolicy="no-referrer"
                      className="w-14 h-14 rounded-full object-cover object-top"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-400 dark:text-gray-500 text-xl">?</div>
                  )}
                  {/* Hover affordance — magnifier overlay */}
                  <div className="absolute inset-0 rounded-full bg-black/30 flex items-center justify-center opacity-0 group-hover/photo:opacity-100 transition-opacity pointer-events-none">
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0zm-6-3v6m-3-3h6" />
                    </svg>
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-1">
                    <span className="font-semibold leading-tight">{c.display_name || c.name}</span>
                    {isSelected && <span className="text-survivor-orange text-lg flex-shrink-0">✓</span>}
                  </div>
                  {c.age && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Age {c.age}{c.hometown ? ` · ${c.hometown}` : ''}</p>}
                  {c.occupation && <p className="text-xs text-gray-400 dark:text-gray-500">{c.occupation}</p>}
                  {c.original_tribe && (
                    <span
                      className="inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full text-white"
                      style={{ backgroundColor: c.tribe_color || '#888' }}
                    >
                      {c.original_tribe}
                    </span>
                  )}
                  {c.is_eliminated && <span className="text-xs text-red-500 mt-1 block">Eliminated Ep {c.eliminated_episode}</span>}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {zoomedCastaway && (
        <CastawayLightbox
          castaway={zoomedCastaway}
          onClose={() => setZoomedCastaway(null)}
        />
      )}
    </div>
  )
}
