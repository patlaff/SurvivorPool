import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useLeague, useMyRoster, useAvailableCastaways, useSwapPerk, useBoostPerk, useSeasonEpisodes } from '../api/leagues'
import { useAuth } from '../hooks/useAuth'

export default function RosterPage() {
  const { slug } = useParams<{ slug: string }>()
  const { user } = useAuth()
  const { data: league } = useLeague(slug!, user?.id)
  const { data: roster } = useMyRoster(slug!, user?.id)
  const { data: available } = useAvailableCastaways(slug!)
  const { data: episodes } = useSeasonEpisodes(league?.season_number ?? 0)
  const swapPerk = useSwapPerk(slug!)
  const boostPerk = useBoostPerk(slug!)

  // Swap window is open while no merge episode has aired yet
  const mergeEpisode = episodes?.find(e => e.is_merge)
  const swapWindowOpen = !mergeEpisode || new Date(mergeEpisode.air_date) > new Date()

  // Boost: eligible episodes are future (not yet aired), unscored, and not the finale
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const boostEligible = episodes?.filter(e =>
    !e.scored_at &&
    !e.is_finale &&
    new Date(e.air_date) > today
  ) ?? []

  const [showSwap, setShowSwap] = useState(false)
  const [outId, setOutId] = useState('')
  const [inId, setInId] = useState('')
  const [showBoost, setShowBoost] = useState(false)
  const [boostEp, setBoostEp] = useState('')
  const [msg, setMsg] = useState('')

  const swap = roster?.perks.find(p => p.perk_type === 'swap')
  const boost = roster?.perks.find(p => p.perk_type === 'boost')

  async function handleSwap(e: React.FormEvent) {
    e.preventDefault()
    try {
      await swapPerk.mutateAsync({ out_id: outId, in_id: inId })
      setMsg('Swap complete!')
      setShowSwap(false)
    } catch { setMsg('Swap failed.') }
  }

  async function handleBoost(e: React.FormEvent) {
    e.preventDefault()
    try {
      await boostPerk.mutateAsync(parseInt(boostEp))
      setMsg(`Boost applied to episode ${boostEp}!`)
      setShowBoost(false)
    } catch { setMsg('Boost failed.') }
  }

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Roster</h1>
        <span className="text-lg font-bold text-survivor-orange">{roster?.total_points ?? 0} pts</span>
      </div>

      {msg && <p className="mb-4 text-sm text-green-600">{msg}</p>}

      <div className="grid gap-3 mb-8">
        {roster?.slots.map(slot => (
          <div key={slot.slot_number} className="card flex items-center gap-3">
            {slot.castaway.image_url ? (
              <img src={slot.castaway.image_url} alt={slot.castaway.name} className="w-12 h-12 rounded-full object-cover object-top flex-shrink-0" />
            ) : (
              <div className="w-12 h-12 rounded-full bg-gray-200 flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{slot.castaway.name}</span>
                {slot.castaway.is_eliminated && (
                  <span className="text-xs text-red-500">Eliminated Ep {slot.castaway.eliminated_episode}</span>
                )}
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {slot.events.map((ev, i) => (
                  <span key={i} className="text-xs bg-gray-100 rounded px-2 py-0.5">
                    {ev.event_name.replace(/_/g, ' ')} +{ev.points}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      <h2 className="text-lg font-semibold mb-3">Perks</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card">
          <h3 className="font-semibold mb-1">🔄 Swap</h3>
          {swap?.used ? (
            <p className="text-sm text-gray-500">Used — swapped {swap.swapped_out_castaway?.name} for {swap.swapped_in_castaway?.name}</p>
          ) : !swapWindowOpen ? (
            <p className="text-sm text-gray-400">
              Window closed — tribes merged
              {mergeEpisode ? ` (Ep ${mergeEpisode.episode_number})` : ''}.
            </p>
          ) : (
            <>
              <p className="text-sm text-gray-500 mb-3">Replace one castaway before the merge.</p>
              <button className="btn-primary text-sm" onClick={() => setShowSwap(true)}>Use Swap</button>
            </>
          )}
          {showSwap && swapWindowOpen && (
            <form onSubmit={handleSwap} className="mt-3 flex flex-col gap-2">
              <select className="input" value={outId} onChange={e => setOutId(e.target.value)} required>
                <option value="">Remove…</option>
                {roster?.slots.map(s => <option key={s.castaway.castaway_id} value={s.castaway.castaway_id}>{s.castaway.name}</option>)}
              </select>
              <select className="input" value={inId} onChange={e => setInId(e.target.value)} required>
                <option value="">Add…</option>
                {available?.map(c => <option key={c.castaway_id} value={c.castaway_id}>{c.name}</option>)}
              </select>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary text-sm flex-1" disabled={swapPerk.isPending}>Confirm</button>
                <button type="button" className="btn-secondary text-sm" onClick={() => setShowSwap(false)}>Cancel</button>
              </div>
            </form>
          )}
        </div>

        <div className="card">
          <h3 className="font-semibold mb-1">⚡ Boost</h3>
          {boost?.used ? (
            <p className="text-sm text-gray-500">Used — 2× on Episode {boost.boost_target_episode}</p>
          ) : boostEligible.length === 0 ? (
            <p className="text-sm text-gray-400">No eligible episodes remaining.</p>
          ) : (
            <>
              <p className="text-sm text-gray-500 mb-3">Double your points for one episode (not the finale).</p>
              <button className="btn-primary text-sm" onClick={() => setShowBoost(true)}>Use Boost</button>
            </>
          )}
          {showBoost && boostEligible.length > 0 && (
            <form onSubmit={handleBoost} className="mt-3 flex flex-col gap-2">
              <select className="input" value={boostEp} onChange={e => setBoostEp(e.target.value)} required>
                <option value="">Select episode…</option>
                {boostEligible.map(ep => (
                  <option key={ep.episode_number} value={String(ep.episode_number)}>
                    Episode {ep.episode_number} ({ep.air_date})
                  </option>
                ))}
              </select>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary text-sm flex-1" disabled={boostPerk.isPending}>Confirm</button>
                <button type="button" className="btn-secondary text-sm" onClick={() => setShowBoost(false)}>Cancel</button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
