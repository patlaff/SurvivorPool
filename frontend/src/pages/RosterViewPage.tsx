import { useParams } from 'react-router-dom'
import { useMemberRoster } from '../api/leagues'

export default function RosterViewPage() {
  const { slug, userId } = useParams<{ slug: string; userId: string }>()
  const { data: roster, isLoading, isError, error } = useMemberRoster(slug!, parseInt(userId!))

  if (isLoading) return <div className="text-gray-400 py-8 text-center">Loading…</div>

  if (isError) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? ''
    if (detail.toLowerCase().includes('hidden')) {
      return (
        <div className="card text-center py-12 text-gray-500">
          <p className="text-xl">🔒</p>
          <p className="text-lg font-medium mt-2">Rosters are hidden during the draft window.</p>
          <p className="text-sm mt-1 text-gray-400">Check back once the draft closes.</p>
        </div>
      )
    }
    return <div className="text-gray-400 py-8 text-center">Roster not found.</div>
  }

  if (!roster) return <div className="text-gray-400 py-8 text-center">Roster not found.</div>

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        {roster.user.avatar_url && (
          <img src={roster.user.avatar_url} className="w-10 h-10 rounded-full" alt="" />
        )}
        <div>
          <h1 className="text-2xl font-bold">{roster.user.display_name}'s Roster</h1>
          <p className="text-sm text-gray-500">{roster.total_points} pts total</p>
        </div>
      </div>

      <div className="grid gap-3">
        {roster.slots.map(slot => (
          <div key={slot.slot_number} className="card flex items-center gap-3">
            {slot.castaway.image_url ? (
              <img src={slot.castaway.image_url} alt={slot.castaway.name} className="w-12 h-12 rounded-full object-cover object-top flex-shrink-0" />
            ) : (
              <div className="w-12 h-12 rounded-full bg-gray-200 flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold">{slot.castaway.name}</span>
                {slot.castaway.is_eliminated && (
                  <span className="text-xs text-red-500">Eliminated Ep {slot.castaway.eliminated_episode}</span>
                )}
              </div>
              {slot.castaway.occupation && <p className="text-xs text-gray-400 mt-0.5">{slot.castaway.occupation}</p>}
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
    </div>
  )
}
