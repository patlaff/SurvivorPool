import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useLeague, useLeaderboard, useDraftWindow, useLeagueActivity, usePicksGrid, useLeagueOverview, useUpdateLeagueSettings, useToggleMemberBuyIn, type DraftWindowPayload, type ActivityEvent, type PicksGridResponse, type LeagueOverviewMember } from '../api/leagues'
import { useAuth } from '../hooks/useAuth'

const COLORS = ['#E8521A', '#F0A500', '#3B82F6', '#10B981', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']

function activityIcon(type: ActivityEvent['type']) {
  if (type === 'draft_saved') return '🗳'
  if (type === 'swap_used') return '🔄'
  return '⚡'
}

function activityDetail(event: ActivityEvent): string {
  if (event.type === 'draft_saved') {
    const castaways = (event.detail.castaways as string[] | undefined) ?? []
    return `Saved picks: ${castaways.join(', ')}`
  }
  if (event.type === 'swap_used') {
    return `Swapped out ${event.detail.dropped ?? '?'} → added ${event.detail.added ?? '?'}`
  }
  return `Doubled points for Ep ${event.detail.episode ?? '?'}`
}

function PicksGridTab({ data, isLoading }: { data: PicksGridResponse | undefined; isLoading: boolean }) {
  if (isLoading) return <p className="text-gray-400 dark:text-gray-500 py-8 text-center">Loading picks…</p>
  if (!data) return null

  if (data.draft_open) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-800">
        Picks are hidden until the draft window closes.
      </div>
    )
  }

  const { players, castaways } = data
  const draftedPlayers = players.filter(p => p.has_drafted)

  if (draftedPlayers.length === 0) {
    return <p className="text-gray-400 dark:text-gray-500 py-8 text-center">No picks saved yet.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="text-sm border-collapse">
        <thead>
          <tr className="text-left border-b dark:border-gray-700">
            <th className="pb-2 pr-4 font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">Castaway</th>
            {draftedPlayers.map(p => (
              <th key={p.user.id} className="pb-2 px-3 text-center font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">
                <div className="flex flex-col items-center gap-1">
                  {p.user.avatar_url && (
                    <img src={p.user.avatar_url} className="w-6 h-6 rounded-full" alt="" />
                  )}
                  <span>{p.user.display_name}</span>
                </div>
              </th>
            ))}
            <th className="pb-2 pl-4 text-center font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">Total</th>
            <th className="pb-2 pl-4 text-center font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">Pts</th>
          </tr>
        </thead>
        <tbody>
          {castaways.map(castaway => (
            <tr key={castaway.castaway_id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
              <td className="py-2 pr-4 whitespace-nowrap">
                <span
                  className={castaway.is_eliminated ? 'line-through text-gray-400' : 'font-medium'}
                  style={!castaway.is_eliminated && castaway.tribe_color ? { color: castaway.tribe_color } : undefined}
                >
                  {castaway.name}
                </span>
                {castaway.is_eliminated && castaway.eliminated_episode != null && (
                  <span className="ml-1 text-xs text-gray-400 dark:text-gray-500">(Ep {castaway.eliminated_episode})</span>
                )}
              </td>
              {draftedPlayers.map(p => (
                <td key={p.user.id} className="py-2 px-3 text-center">
                  {p.picks.includes(castaway.castaway_id) ? (
                    <span className="inline-block w-5 h-5 rounded-full bg-survivor-orange text-white text-xs leading-5 font-bold">✓</span>
                  ) : (
                    <span className="text-gray-200">·</span>
                  )}
                </td>
              ))}
              <td className="py-2 pl-4 text-center font-semibold text-gray-700 dark:text-gray-300">
                {castaway.pick_count > 0 ? castaway.pick_count : <span className="text-gray-300 dark:text-gray-600">0</span>}
              </td>
              <td className="py-2 pl-4 text-center font-semibold text-gray-700 dark:text-gray-300">
                {castaway.total_points > 0 ? castaway.total_points : <span className="text-gray-300 dark:text-gray-600">0</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ActivityLogTab({ events, isLoading }: { events: ActivityEvent[] | undefined; isLoading: boolean }) {
  if (isLoading) return <p className="text-gray-400 dark:text-gray-500 py-8 text-center">Loading activity…</p>
  if (!events || events.length === 0) return <p className="text-gray-400 dark:text-gray-500 py-8 text-center">No activity yet in this league.</p>
  return (
    <div className="space-y-3">
      {events.map((event, idx) => (
        <div key={idx} className="flex items-start gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
          <span className="text-xl mt-0.5">{activityIcon(event.type)}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {event.user.avatar_url && (
                <img src={event.user.avatar_url} className="w-5 h-5 rounded-full" alt="" />
              )}
              <span className="font-medium text-sm">{event.user.display_name}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">{new Date(event.timestamp).toLocaleString()}</span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">{activityDetail(event)}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function LeagueOverviewTab({
  slug,
  members,
  isLoading,
  buyInAmount,
  venmoHandle,
}: {
  slug: string
  members: LeagueOverviewMember[] | undefined
  isLoading: boolean
  buyInAmount: string | null
  venmoHandle: string | null
}) {
  const [buyInInput, setBuyInInput] = useState(buyInAmount ?? '')
  const [venmoInput, setVenmoInput] = useState(venmoHandle ?? '')
  const [settingsFeedback, setSettingsFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const updateSettings = useUpdateLeagueSettings(slug)
  const toggleBuyIn = useToggleMemberBuyIn(slug)

  const hasBuyIn = buyInInput.trim() !== ''

  const handleSaveSettings = async () => {
    try {
      await updateSettings.mutateAsync({
        buy_in_amount: hasBuyIn ? buyInInput.trim() : null,
        // Clear venmo if buy-in is removed
        venmo_handle: hasBuyIn && venmoInput.trim() !== '' ? venmoInput.trim() : null,
      })
      setSettingsFeedback({ type: 'success', message: 'Settings saved.' })
      setTimeout(() => setSettingsFeedback(null), 4000)
    } catch {
      setSettingsFeedback({ type: 'error', message: 'Failed to save settings.' })
      setTimeout(() => setSettingsFeedback(null), 4000)
    }
  }

  return (
    <div className="space-y-6">
      {/* Buy-in settings */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Buy-in Settings</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 dark:text-gray-400">Buy-in amount ($)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 20"
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 focus:border-survivor-orange focus:outline-none focus:ring-1 focus:ring-survivor-orange w-36"
              value={buyInInput}
              onChange={e => setBuyInInput(e.target.value)}
            />
          </div>
          {hasBuyIn && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500 dark:text-gray-400">Venmo handle</label>
              <input
                type="text"
                placeholder="@yourhandle"
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 focus:border-survivor-orange focus:outline-none focus:ring-1 focus:ring-survivor-orange w-44"
                value={venmoInput}
                onChange={e => setVenmoInput(e.target.value)}
              />
            </div>
          )}
          <button
            className="btn-primary text-xs px-3 py-1.5"
            onClick={handleSaveSettings}
            disabled={updateSettings.isPending}
          >
            Save
          </button>
        </div>
        {settingsFeedback && (
          <p className={`mt-2 text-xs ${settingsFeedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {settingsFeedback.message}
          </p>
        )}
      </div>

      {/* Members table */}
      <div>
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Members</h2>
        {isLoading && <p className="text-gray-400 dark:text-gray-500 py-4 text-center">Loading members…</p>}
        {!isLoading && members && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                  <th className="pb-2 pr-4">Player</th>
                  <th className="pb-2 pr-4 text-center">Picks made</th>
                  <th className="pb-2 text-center">Bought in?</th>
                </tr>
              </thead>
              <tbody>
                {members.map(member => (
                  <tr key={member.user.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="py-3 pr-4">
                      <span className="flex items-center gap-2">
                        {member.user.avatar_url && (
                          <img src={member.user.avatar_url} className="w-6 h-6 rounded-full" alt="" />
                        )}
                        <span>{member.user.display_name}</span>
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-center font-medium">
                      {member.pick_count > 0
                        ? <span className="text-gray-800 dark:text-gray-200">{member.pick_count}</span>
                        : <span className="text-gray-400 dark:text-gray-500">0</span>
                      }
                    </td>
                    <td className="py-3 text-center">
                      <input
                        type="checkbox"
                        checked={member.bought_in}
                        onChange={e => toggleBuyIn.mutate({ userId: member.user.id, bought_in: e.target.checked })}
                        className="w-4 h-4 accent-survivor-orange cursor-pointer"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function formatLastUpdated(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return 'less than an hour ago'
  if (hours === 1) return '1 hour ago'
  if (hours < 24) return `${hours} hours ago`
  const days = Math.floor(hours / 24)
  return days === 1 ? '1 day ago' : `${days} days ago`
}

export default function LeaguePage() {
  const { slug } = useParams<{ slug: string }>()
  const { user } = useAuth()
  const { data: league } = useLeague(slug!, user?.id)
  const { data: leaderboardData, isLoading } = useLeaderboard(slug!)
  const [tab, setTab] = useState<'leaderboard' | 'chart' | 'picks' | 'activity' | 'overview'>('leaderboard')
  const draftWindowMutation = useDraftWindow(slug!)
  const [scheduleInput, setScheduleInput] = useState('')
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const isOwner = user?.id === league?.owner?.id
  const { data: activityData, isLoading: activityLoading } = useLeagueActivity(slug!, isOwner)
  const { data: picksGridData, isLoading: picksGridLoading } = usePicksGrid(slug!)
  const { data: overviewData, isLoading: overviewLoading } = useLeagueOverview(slug!, isOwner)

  const handleDraftWindowAction = async (payload: DraftWindowPayload) => {
    try {
      await draftWindowMutation.mutateAsync(payload)
      setFeedback({ type: 'success', message: 'Draft window updated.' })
      setTimeout(() => setFeedback(null), 4000)
    } catch {
      setFeedback({ type: 'error', message: 'Failed to update draft window.' })
      setTimeout(() => setFeedback(null), 4000)
    }
  }

  const leaderboard = leaderboardData?.entries
  const lastScoredAt = leaderboardData?.last_scored_at ?? null
  // When draft is open, other players' episode arrays are empty ([]).
  // Derive column headers from the current user's own entry (always full),
  // falling back to any non-hidden entry, then the first entry.
  const episodeColumns =
    leaderboard?.find(e => e.user.id === user?.id)?.episodes ??
    leaderboard?.find(e => !e.roster_hidden)?.episodes ??
    leaderboard?.[0]?.episodes ??
    []

  const isStale = lastScoredAt
    ? Date.now() - new Date(lastScoredAt).getTime() > 8 * 24 * 3600 * 1000
    : false

  const chartData = (() => {
    if (!leaderboard) return []
    const epNums = [...new Set(leaderboard.flatMap(e => e.episodes.map(ep => ep.episode_number)))].sort((a, b) => a - b)
    return epNums.map(ep => {
      const row: Record<string, number | string> = { episode: `Ep ${ep}` }
      leaderboard.forEach(entry => {
        const cumulative = entry.episodes
          .filter(e => e.episode_number <= ep)
          .reduce((sum, e) => sum + e.final_points, 0)
        row[entry.user.display_name] = cumulative
      })
      return row
    })
  })()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{league?.name ?? '…'}</h1>
          {league?.owner && (
            <p className="text-sm text-gray-500 dark:text-gray-400">Owned by {league.owner.display_name}</p>
          )}
        </div>
        <div className="flex gap-3">
          {league?.is_archived
            ? <span className="inline-flex items-center px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700">Archived</span>
            : <>
                <Link to={`/leagues/${slug}/draft`} className="btn-secondary">Draft</Link>
                <Link to={`/leagues/${slug}/roster`} className="btn-secondary">My Roster</Link>
              </>
          }
        </div>
      </div>

      {league?.is_archived && (
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 mb-6 text-sm text-gray-600 dark:text-gray-400">
          This league has concluded. All scores and rosters are preserved as a read-only record.
        </div>
      )}

      {league?.buy_in_amount && (
        <div className="card mb-6 flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-2 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Buy-in:</span>
            <span className="font-semibold text-gray-800 dark:text-gray-200">${parseFloat(league.buy_in_amount).toFixed(2)}</span>
          </span>
          {league.venmo_handle && (
            <span className="flex items-center gap-2 text-sm">
              <span className="text-gray-500 dark:text-gray-400">Venmo:</span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">{league.venmo_handle}</span>
            </span>
          )}
        </div>
      )}

      {league?.owner?.id === user?.id && league?.invite_code && (
        <div className="card mb-6 flex items-center gap-4">
          <span className="text-sm text-gray-500 dark:text-gray-400">Invite code:</span>
          <span className="font-mono font-bold text-survivor-orange text-lg tracking-widest">{league.invite_code}</span>
          <button onClick={() => navigator.clipboard.writeText(league.invite_code!)} className="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">Copy</button>
        </div>
      )}

      {isOwner && league && (
        <div className="card mb-6">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Draft Settings</h2>
          <div className="flex flex-wrap items-start gap-4">

            {/* Status badge */}
            <div className="flex items-center gap-2 pt-1">
              <span className="text-sm text-gray-500 dark:text-gray-400">Status:</span>
              {league.draft_open
                ? <span className="badge-green">● Open</span>
                : <span className="badge-red">● Closed</span>
              }
              {league.draft_close_at && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  (closes {new Date(league.draft_close_at).toLocaleString()})
                </span>
              )}
            </div>

            {/* Quick-action buttons */}
            <div className="flex flex-wrap gap-2">
              <button
                className="btn-secondary text-xs px-3 py-1.5"
                onClick={() => handleDraftWindowAction({ draft_close_at: new Date().toISOString(), draft_force_open: false })}
                disabled={draftWindowMutation.isPending}
              >
                Close now
              </button>
              <button
                className="btn-secondary text-xs px-3 py-1.5"
                onClick={() => handleDraftWindowAction({ draft_close_at: null, draft_force_open: true })}
                disabled={draftWindowMutation.isPending}
              >
                Reopen draft
              </button>
              <button
                className="btn-secondary text-xs px-3 py-1.5"
                onClick={() => handleDraftWindowAction({ draft_close_at: null, draft_force_open: false })}
                disabled={draftWindowMutation.isPending}
              >
                Revert to default
              </button>
            </div>

            {/* Schedule close */}
            <div className="flex items-center gap-2">
              <input
                type="datetime-local"
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 focus:border-survivor-orange focus:outline-none focus:ring-1 focus:ring-survivor-orange"
                value={scheduleInput}
                onChange={e => setScheduleInput(e.target.value)}
              />
              <button
                className="btn-primary text-xs px-3 py-1.5"
                onClick={() => {
                  if (!scheduleInput) return
                  handleDraftWindowAction({ draft_close_at: new Date(scheduleInput).toISOString(), draft_force_open: false })
                  setScheduleInput('')
                }}
                disabled={!scheduleInput || draftWindowMutation.isPending}
              >
                Schedule
              </button>
            </div>
          </div>

          {feedback && (
            <p className={`mt-2 text-xs ${feedback.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
              {feedback.message}
            </p>
          )}
        </div>
      )}

      <div className="flex gap-4 mb-4 border-b dark:border-gray-700">
        <button className={`pb-2 text-sm font-medium ${tab === 'leaderboard' ? 'border-b-2 border-survivor-orange text-survivor-orange' : 'text-gray-500 dark:text-gray-400'}`} onClick={() => setTab('leaderboard')}>Leaderboard</button>
        <button className={`pb-2 text-sm font-medium ${tab === 'chart' ? 'border-b-2 border-survivor-orange text-survivor-orange' : 'text-gray-500 dark:text-gray-400'}`} onClick={() => setTab('chart')}>Points Chart</button>
        <button className={`pb-2 text-sm font-medium ${tab === 'picks' ? 'border-b-2 border-survivor-orange text-survivor-orange' : 'text-gray-500 dark:text-gray-400'}`} onClick={() => setTab('picks')}>Picks Grid</button>
        {isOwner && (
          <button className={`pb-2 text-sm font-medium ${tab === 'activity' ? 'border-b-2 border-survivor-orange text-survivor-orange' : 'text-gray-500 dark:text-gray-400'}`} onClick={() => setTab('activity')}>Activity Log</button>
        )}
        {isOwner && (
          <button className={`pb-2 text-sm font-medium ${tab === 'overview' ? 'border-b-2 border-survivor-orange text-survivor-orange' : 'text-gray-500 dark:text-gray-400'}`} onClick={() => setTab('overview')}>League Overview</button>
        )}
      </div>

      {isStale && tab !== 'activity' && tab !== 'picks' && tab !== 'overview' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 mb-4 text-sm text-yellow-800">
          Scores haven't updated in over 8 days. The data source may be lagging.
        </div>
      )}

      {isLoading && tab !== 'activity' && tab !== 'picks' && tab !== 'overview' && <div className="text-gray-400 dark:text-gray-500 py-8 text-center">Loading scores…</div>}

      {tab === 'leaderboard' && leaderboard && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                <th className="pb-2 pr-4">#</th>
                <th className="pb-2 pr-4">Player</th>
                {episodeColumns.map(ep => (
                  <th key={ep.episode_number} className="pb-2 pr-2 text-right">Ep {ep.episode_number}</th>
                ))}
                <th className="pb-2 text-right font-semibold">Total</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map(entry => (
                <tr key={entry.user.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="py-3 pr-4 font-bold text-gray-400 dark:text-gray-500">#{entry.rank}</td>
                  <td className="py-3 pr-4">
                    {entry.roster_hidden
                      ? (
                        <span className="flex items-center gap-2">
                          {entry.user.avatar_url && <img src={entry.user.avatar_url} className="w-6 h-6 rounded-full" alt="" />}
                          <span>{entry.user.display_name}</span>
                          <span className="text-gray-400 dark:text-gray-500 text-xs" title="Roster hidden during draft window">🔒</span>
                        </span>
                      ) : (
                        <Link to={`/leagues/${slug}/roster/${entry.user.id}`} className="flex items-center gap-2 hover:underline">
                          {entry.user.avatar_url && <img src={entry.user.avatar_url} className="w-6 h-6 rounded-full" alt="" />}
                          <span>{entry.user.display_name}</span>
                        </Link>
                      )
                    }
                  </td>
                  {entry.roster_hidden
                    ? episodeColumns.map(ep => (
                        <td key={ep.episode_number} className="py-3 pr-2 text-right text-gray-300 dark:text-gray-600">—</td>
                      ))
                    : entry.episodes.map(ep => (
                        <td key={ep.episode_number} className="py-3 pr-2 text-right text-gray-600 dark:text-gray-400">
                          {ep.final_points > ep.raw_points && <span title="Boosted" className="text-survivor-gold mr-1">⚡</span>}
                          {ep.final_points}
                        </td>
                      ))
                  }
                  <td className="py-3 text-right font-bold">
                    {entry.roster_hidden ? <span className="text-gray-300 dark:text-gray-600">—</span> : entry.total_points}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'chart' && leaderboard && chartData.length > 0 && (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="episode" />
              <YAxis />
              <Tooltip />
              <Legend />
              {leaderboard.map((entry, i) => (
                <Line key={entry.user.id} type="monotone" dataKey={entry.user.display_name} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {leaderboard?.length === 0 && tab !== 'activity' && tab !== 'picks' && tab !== 'overview' && (
        <p className="text-center text-gray-400 dark:text-gray-500 py-8">No episodes scored yet.</p>
      )}

      {tab === 'picks' && (
        <PicksGridTab data={picksGridData} isLoading={picksGridLoading} />
      )}

      {tab === 'activity' && isOwner && (
        <ActivityLogTab events={activityData} isLoading={activityLoading} />
      )}

      {tab === 'overview' && isOwner && (
        <LeagueOverviewTab
          slug={slug!}
          members={overviewData?.members}
          isLoading={overviewLoading}
          buyInAmount={league?.buy_in_amount ?? null}
          venmoHandle={league?.venmo_handle ?? null}
        />
      )}

      {lastScoredAt && tab !== 'activity' && tab !== 'picks' && tab !== 'overview' && (
        <p className="mt-4 text-xs text-gray-400 dark:text-gray-500 text-right">Last updated {formatLastUpdated(lastScoredAt)}</p>
      )}
    </div>
  )
}
