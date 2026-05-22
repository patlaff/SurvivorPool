import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useLeague, useSeasonCastaways, useDraft, useSaveDraft } from '../api/leagues'
import { useAuth } from '../hooks/useAuth'

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
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">Draft — {league?.name}</h1>
        <span className={`text-sm font-medium ${draftOpen ? 'text-green-600' : 'text-gray-400'}`}>
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
        <span className="text-sm text-gray-500 whitespace-nowrap">{selected.size} / 5 selected</span>
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
              onClick={() => toggle(c.castaway_id)}
              disabled={!draftOpen || (!isSelected && (isEliminated || selected.size >= 5))}
              className={`card text-left transition-all ${isSelected ? 'border-survivor-orange bg-orange-50' : 'hover:border-gray-300'} ${isEliminated && !isSelected ? 'opacity-50 cursor-not-allowed' : ''} ${!draftOpen ? 'cursor-default' : ''}`}
            >
              <div className="flex items-start justify-between">
                <span className="font-semibold">{c.name}</span>
                {isSelected && <span className="text-survivor-orange text-lg">✓</span>}
              </div>
              {c.age && <p className="text-xs text-gray-500 mt-1">Age {c.age}{c.hometown ? ` · ${c.hometown}` : ''}</p>}
              {c.occupation && <p className="text-xs text-gray-400">{c.occupation}</p>}
              {c.is_eliminated && <span className="text-xs text-red-500 mt-1 block">Eliminated Ep {c.eliminated_episode}</span>}
            </button>
          )
        })}
      </div>
    </div>
  )
}
