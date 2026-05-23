import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  useAdminLeagues,
  useAdminCastaways,
  useUpdateCastawayAlias,
  useArchiveSeason,
  useProgressSeason,
  useUnarchiveSeason,
  useCreateTestLeague,
  useScoringConfig,
  useSaveConfig,
  useRescoreSeason,
  useScoreUnscored,
  useScoringSummary,
  type AdminCastaway,
} from '../api/admin'
import { useActiveSeason } from '../api/info'

type Tab = 'leagues' | 'scoring' | 'config' | 'castaways'

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('leagues')

  return (
    <div className="max-w-5xl">
      <h1 className="text-2xl font-bold mb-6">
        Superadmin Panel
        <span className="ml-3 text-xs font-semibold text-survivor-orange border border-survivor-orange rounded px-2 py-0.5">
          ADMIN
        </span>
      </h1>

      <div className="flex gap-1 mb-6 border-b border-gray-200 dark:border-gray-700">
        {(['leagues', 'scoring', 'config', 'castaways'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              tab === t
                ? 'border-survivor-orange text-survivor-orange'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {t === 'leagues' ? 'Leagues' : t === 'scoring' ? 'Scoring Summary' : t === 'config' ? 'Scoring Config' : 'Castaways'}
          </button>
        ))}
      </div>

      {tab === 'leagues' && <LeaguesTab />}
      {tab === 'scoring' && <ScoringTab />}
      {tab === 'config' && <ConfigTab />}
      {tab === 'castaways' && <CastawaysTab />}
    </div>
  )
}

// ── Leagues Tab ───────────────────────────────────────────────────────────────

function LeaguesTab() {
  const { data: leagues, isLoading } = useAdminLeagues()
  const { data: activeSeasonData } = useActiveSeason()
  const activeSeason = activeSeasonData?.season
  const ACTIVE_SEASON = activeSeason?.season_number ?? 0
  const allowsNewLeagues = activeSeason?.allows_new_leagues ?? true
  const nextDetectedAt = activeSeason?.next_detected_at ?? null
  const nextNum = ACTIVE_SEASON + 1

  const archiveSeason = useArchiveSeason()
  const progressSeason = useProgressSeason()
  const unarchiveSeason = useUnarchiveSeason()
  const createTestLeague = useCreateTestLeague()

  const [newName, setNewName] = useState('')
  const [created, setCreated] = useState<{ slug: string; invite_code: string; name: string } | null>(null)
  const [createError, setCreateError] = useState('')
  const [actionMsg, setActionMsg] = useState('')
  const [pendingAction, setPendingAction] = useState(false)

  const activeLeagues = leagues?.filter(l => !l.is_archived) ?? []
  const archivedLeagues = leagues?.filter(l => l.is_archived) ?? []

  // State 1: season still live → Archive button
  // State 2: archived, no next data yet → Watching
  // State 3: next data detected → Progress button
  const progressionState: 1 | 2 | 3 = allowsNewLeagues ? 1 : nextDetectedAt ? 3 : 2

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreateError('')
    setCreated(null)
    try {
      const result = await createTestLeague.mutateAsync(newName)
      setCreated({ slug: result.slug, invite_code: result.invite_code, name: result.name })
      setNewName('')
    } catch {
      setCreateError('Failed to create test league.')
    }
  }

  async function handleArchive() {
    setActionMsg('')
    try {
      const result = await archiveSeason.mutateAsync(ACTIVE_SEASON)
      setActionMsg(result.detail)
      setPendingAction(false)
    } catch {
      setActionMsg('Archive failed — check backend logs.')
      setPendingAction(false)
    }
  }

  async function handleProgress() {
    setActionMsg('')
    try {
      const result = await progressSeason.mutateAsync()
      setActionMsg(result.detail)
      setPendingAction(false)
    } catch {
      setActionMsg('Progression failed — check backend logs.')
      setPendingAction(false)
    }
  }

  async function handleUnarchive() {
    setActionMsg('')
    try {
      const result = await unarchiveSeason.mutateAsync(ACTIVE_SEASON)
      setActionMsg(result.detail)
    } catch {
      setActionMsg('Unarchive failed — check backend logs.')
    }
  }

  return (
    <div>
      {/* Current season card */}
      <div className="card mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wider font-medium mb-1">Current Season</p>
            <h2 className="text-lg font-bold">
              {activeSeason ? `Season ${activeSeason.season_number} — ${activeSeason.name}` : '—'}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {allowsNewLeagues
                ? `${activeLeagues.length} active league${activeLeagues.length !== 1 ? 's' : ''}`
                : `${archivedLeagues.filter(l => l.season_number === ACTIVE_SEASON).length} archived league${archivedLeagues.filter(l => l.season_number === ACTIVE_SEASON).length !== 1 ? 's' : ''} · dormant`
              }
            </p>
          </div>
          <div className="shrink-0">
            {allowsNewLeagues
              ? <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">● Active</span>
              : nextDetectedAt
                ? <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">● Next Season Ready</span>
                : <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">● Dormant</span>
            }
          </div>
        </div>
      </div>

      {/* Season progression widget */}
      {progressionState === 1 && (
        <div className="card mb-6 flex items-center justify-between gap-4">
          <div>
            <h2 className="font-semibold text-red-700">Archive Season {ACTIVE_SEASON || '—'}</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Closes all drafts and marks every league read-only. Do this once the season finale has aired.
            </p>
            {actionMsg && (
              <p className={`text-sm mt-1 ${actionMsg.includes('failed') ? 'text-red-600' : 'text-green-600'}`}>
                {actionMsg}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            {!pendingAction ? (
              <button
                className="btn-secondary text-xs px-3 py-1.5 text-red-600 border-red-300 hover:bg-red-50"
                onClick={() => setPendingAction(true)}
                disabled={ACTIVE_SEASON === 0}
              >
                Archive Season {ACTIVE_SEASON || '—'}
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-xs text-red-700 dark:text-red-400 font-medium">Are you sure? This is irreversible.</span>
                <button
                  className="text-xs px-3 py-1.5 rounded border border-red-500 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/50 font-semibold"
                  onClick={handleArchive}
                  disabled={archiveSeason.isPending}
                >
                  {archiveSeason.isPending ? 'Archiving…' : 'Confirm Archive'}
                </button>
                <button
                  className="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300"
                  onClick={() => setPendingAction(false)}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {progressionState === 2 && (
        <div className="card mb-6">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">⏳ Watching for Season {nextNum} data…</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            The daily sync checks automatically at 20:00 PT. You'll get an email when it appears.
          </p>
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-gray-500 italic">For testing only</span>
            <button
              className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 underline"
              onClick={handleUnarchive}
              disabled={unarchiveSeason.isPending}
            >
              {unarchiveSeason.isPending ? 'Reverting…' : 'Unarchive Season ' + ACTIVE_SEASON}
            </button>
          </div>
          {actionMsg && (
            <p className={`text-xs mt-2 ${actionMsg.includes('failed') ? 'text-red-500' : 'text-green-600'}`}>
              {actionMsg}
            </p>
          )}
        </div>
      )}

      {progressionState === 3 && (
        <div className="card mb-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="font-semibold text-green-700">Season {nextNum} data detected</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Detected {new Date(nextDetectedAt!).toLocaleDateString()}.
                Progressing will sync Season {nextNum} and allow new leagues to be created.
              </p>
              {actionMsg && (
                <p className={`text-sm mt-1 ${actionMsg.includes('failed') ? 'text-red-600' : 'text-green-600'}`}>
                  {actionMsg}
                </p>
              )}
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              {!pendingAction ? (
                <button
                  className="btn-primary text-sm whitespace-nowrap"
                  onClick={() => setPendingAction(true)}
                >
                  Progress Season {ACTIVE_SEASON} → {nextNum}
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-700 dark:text-gray-300 font-medium">
                    Archives S{ACTIVE_SEASON} leagues and syncs S{nextNum}. Takes ~60s.
                  </span>
                  <button
                    className="text-xs px-3 py-1.5 rounded border border-green-600 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-900/50 font-semibold"
                    onClick={handleProgress}
                    disabled={progressSeason.isPending}
                  >
                    {progressSeason.isPending ? 'Progressing…' : 'Confirm'}
                  </button>
                  <button
                    className="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300"
                    onClick={() => setPendingAction(false)}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-gray-500 italic">For testing only</span>
            <button
              className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 underline"
              onClick={handleUnarchive}
              disabled={unarchiveSeason.isPending}
            >
              {unarchiveSeason.isPending ? 'Reverting…' : 'Unarchive Season ' + ACTIVE_SEASON}
            </button>
          </div>
        </div>
      )}

      {/* Create test league */}
      <div className="card mb-6">
        <h2 className="font-semibold mb-3">Create Test League</h2>
        <form onSubmit={handleCreate} className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="label">League Name</label>
            <input
              className="input"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="Test League Alpha"
              required
            />
          </div>
          <button type="submit" className="btn-primary" disabled={createTestLeague.isPending}>
            Create Test League
          </button>
        </form>
        {createError && <p className="mt-2 text-sm text-red-600">{createError}</p>}
        {created && (
          <div className="mt-3 p-3 bg-green-50 rounded text-sm">
            <p className="font-medium text-green-800">
              Created: <Link to={`/leagues/${created.slug}`} className="underline">{created.name}</Link>
            </p>
            <p className="text-green-700 mt-1">
              Invite code: <code className="font-mono font-bold">{created.invite_code}</code>
            </p>
          </div>
        )}
      </div>

      {/* Active leagues table */}
      <div className="card overflow-hidden p-0 mb-6">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
          <h2 className="font-semibold">Active Leagues ({activeLeagues.length})</h2>
        </div>
        {isLoading ? (
          <div className="p-4 text-gray-400 dark:text-gray-500">Loading...</div>
        ) : activeLeagues.length === 0 ? (
          <div className="p-4 text-sm text-gray-400 dark:text-gray-500">No active leagues.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-2">Name</th>
                  <th className="px-4 py-2">Owner</th>
                  <th className="px-4 py-2">Members</th>
                  <th className="px-4 py-2">Draft</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Invite</th>
                  <th className="px-4 py-2">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {activeLeagues.map(league => (
                  <tr key={league.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-4 py-2">
                      <Link to={`/leagues/${league.slug}`} className="text-survivor-orange hover:underline font-medium">
                        {league.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      <div className="font-medium">{league.owner.display_name}</div>
                      <div className="text-gray-400 dark:text-gray-500 text-xs">{league.owner.email}</div>
                    </td>
                    <td className="px-4 py-2 text-center">{league.member_count}</td>
                    <td className="px-4 py-2">
                      {league.draft_open
                        ? <span className="badge-green">Open</span>
                        : <span className="badge-gray">Closed</span>}
                    </td>
                    <td className="px-4 py-2">
                      {league.is_test && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300">
                          TEST
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{league.invite_code}</td>
                    <td className="px-4 py-2 text-gray-500 dark:text-gray-400 text-xs">
                      {new Date(league.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Archived leagues table */}
      {archivedLeagues.length > 0 && (
        <div className="card overflow-hidden p-0">
          <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
            <h2 className="font-semibold text-gray-500 dark:text-gray-400">Archived Leagues ({archivedLeagues.length})</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-2">Name</th>
                  <th className="px-4 py-2">Season</th>
                  <th className="px-4 py-2">Owner</th>
                  <th className="px-4 py-2">Members</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {archivedLeagues.map(league => (
                  <tr key={league.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 opacity-75">
                    <td className="px-4 py-2">
                      <Link to={`/leagues/${league.slug}`} className="text-gray-600 dark:text-gray-400 hover:underline font-medium">
                        {league.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-gray-500 dark:text-gray-400">S{league.season_number}</td>
                    <td className="px-4 py-2">
                      <div className="font-medium">{league.owner.display_name}</div>
                      <div className="text-gray-400 dark:text-gray-500 text-xs">{league.owner.email}</div>
                    </td>
                    <td className="px-4 py-2 text-center">{league.member_count}</td>
                    <td className="px-4 py-2">
                      {league.is_test && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300">
                          TEST
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-gray-500 dark:text-gray-400 text-xs">
                      {new Date(league.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Scoring Summary Tab ───────────────────────────────────────────────────────

function ScoringTab() {
  const { data: activeSeasonData } = useActiveSeason()
  const ACTIVE_SEASON = activeSeasonData?.season?.season_number ?? 0

  const { data, isLoading, refetch } = useScoringSummary(ACTIVE_SEASON)
  const scoreUnscored = useScoreUnscored()
  const [openEpisode, setOpenEpisode] = useState<number | null>(null)
  const [scoreMsg, setScoreMsg] = useState('')

  async function handleScoreUnscored() {
    setScoreMsg('')
    try {
      const result = await scoreUnscored.mutateAsync(ACTIVE_SEASON)
      if (result.episodes_scored === 0 && result.episodes_attempted === 0) {
        setScoreMsg('All aired episodes are already scored.')
      } else {
        setScoreMsg(`Scored ${result.episodes_scored} of ${result.episodes_attempted} episode(s).`)
        refetch()
      }
    } catch {
      setScoreMsg('Scoring failed — check backend logs.')
    }
  }

  if (isLoading) return <div className="text-gray-400 dark:text-gray-500">Loading scoring data...</div>

  return (
    <div>
      {/* Score unscored episodes */}
      <div className="card mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-semibold">Score Past Episodes</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Runs the scoring pipeline for every aired episode that hasn't been scored yet.
          </p>
          {scoreMsg && (
            <p className={`text-sm mt-1 ${scoreMsg.includes('failed') ? 'text-red-600' : 'text-green-600'}`}>
              {scoreMsg}
            </p>
          )}
        </div>
        <button
          className="btn-primary text-sm whitespace-nowrap"
          onClick={handleScoreUnscored}
          disabled={scoreUnscored.isPending || ACTIVE_SEASON === 0}
        >
          {scoreUnscored.isPending ? 'Scoring…' : 'Score All Unscored'}
        </button>
      </div>

      {/* Castaway totals */}
      <div className="card mb-6">
        <h2 className="font-semibold mb-3">
          Castaway Totals — Season {data?.season_number ?? ACTIVE_SEASON}
          <span className="ml-2 text-xs text-gray-400 dark:text-gray-500 font-normal">
            ({data?.scored_episodes.length ?? 0} episodes scored)
          </span>
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2">Rank</th>
                <th className="px-3 py-2">Castaway</th>
                <th className="px-3 py-2 text-right">Total Pts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(data?.castaway_totals ?? []).map((c, i) => (
                <tr key={c.castaway_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-3 py-1.5 text-gray-400 dark:text-gray-500">{i + 1}</td>
                  <td className="px-3 py-1.5 font-medium">
                    {c.name}
                    {c.is_eliminated && (
                      <span className="ml-2 text-xs text-red-400">eliminated</span>
                    )}
                  </td>
                  <td className="px-3 py-1.5 text-right font-semibold">{c.total_points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Per-episode accordion */}
      <div className="space-y-2">
        {(data?.scored_episodes ?? []).map(ep => (
          <div key={ep.episode_number} className="card p-0 overflow-hidden">
            <button
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50"
              onClick={() => setOpenEpisode(openEpisode === ep.episode_number ? null : ep.episode_number)}
            >
              <span className="font-medium">
                Episode {ep.episode_number}
                <span className="ml-2 text-sm text-gray-400 dark:text-gray-500">{ep.air_date}</span>
              </span>
              <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                <span>{ep.events.length} events</span>
                <span className="font-semibold text-gray-700 dark:text-gray-300">{ep.episode_total} pts total</span>
                <span>{openEpisode === ep.episode_number ? '▲' : '▼'}</span>
              </div>
            </button>
            {openEpisode === ep.episode_number && (
              <div className="border-t border-gray-100 dark:border-gray-700 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-2 text-left">Castaway</th>
                      <th className="px-4 py-2 text-left">Event</th>
                      <th className="px-4 py-2 text-right">Pts</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {ep.events.map((ev, i) => (
                      <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-4 py-1.5 font-medium">{ev.castaway_name}</td>
                        <td className="px-4 py-1.5 font-mono text-xs text-gray-600 dark:text-gray-400">
                          {ev.event_name.replace(/_/g, ' ')}
                        </td>
                        <td className="px-4 py-1.5 text-right font-semibold">+{ev.points}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>

      {(data?.scored_episodes.length ?? 0) === 0 && !isLoading && (
        <p className="text-gray-400 dark:text-gray-500 text-sm">No episodes have been scored yet.</p>
      )}
    </div>
  )
}

// ── Scoring Config Tab ────────────────────────────────────────────────────────

function ConfigTab() {
  const { data: activeSeasonData } = useActiveSeason()
  const ACTIVE_SEASON = activeSeasonData?.season?.season_number ?? 0

  const { data, isLoading } = useScoringConfig()
  const saveConfig = useSaveConfig()
  const rescoreSeason = useRescoreSeason()

  const [localConfig, setLocalConfig] = useState<Record<string, number> | null>(null)
  const [saveMsg, setSaveMsg] = useState('')
  const [rescoreMsg, setRescoreMsg] = useState('')

  const config = localConfig ?? data?.config ?? {}

  function handleChange(key: string, value: string) {
    const num = parseInt(value, 10)
    if (isNaN(num)) return
    setLocalConfig({ ...config, [key]: num })
    setSaveMsg('')
  }

  async function handleSave() {
    setSaveMsg('')
    try {
      await saveConfig.mutateAsync(config)
      setLocalConfig(null)
      setSaveMsg('Config saved successfully.')
    } catch {
      setSaveMsg('Failed to save config.')
    }
  }

  async function handleRescore() {
    setRescoreMsg('')
    try {
      const result = await rescoreSeason.mutateAsync(ACTIVE_SEASON)
      setRescoreMsg(`Re-scored ${result.episodes_rescored} episodes, updated ${result.rosters_updated} roster scores.`)
    } catch {
      setRescoreMsg('Re-score failed.')
    }
  }

  if (isLoading) return <div className="text-gray-400 dark:text-gray-500">Loading config...</div>

  const isDirty = localConfig !== null

  return (
    <div>
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Scoring Config — scoring_config.json</h2>
          <div className="flex gap-2">
            <button
              className="btn-primary text-sm"
              onClick={handleSave}
              disabled={saveConfig.isPending || !isDirty}
            >
              {saveConfig.isPending ? 'Saving…' : 'Save Config'}
            </button>
            <button
              className="btn-secondary text-sm"
              onClick={handleRescore}
              disabled={rescoreSeason.isPending || ACTIVE_SEASON === 0}
            >
              {rescoreSeason.isPending ? 'Re-scoring…' : 'Re-score Season'}
            </button>
          </div>
        </div>

        {saveMsg && (
          <p className={`mb-3 text-sm ${saveMsg.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
            {saveMsg}
          </p>
        )}
        {rescoreMsg && (
          <p className={`mb-3 text-sm ${rescoreMsg.includes('failed') ? 'text-red-600' : 'text-green-600'}`}>
            {rescoreMsg}
          </p>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2 text-left">Event</th>
                <th className="px-3 py-2 text-right w-32">Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {Object.entries(config).sort(([a], [b]) => a.localeCompare(b)).map(([key, val]) => (
                <tr key={key} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-3 py-1.5 font-mono text-xs">{key}</td>
                  <td className="px-3 py-1.5 text-right">
                    <input
                      type="number"
                      className="w-20 text-right border border-gray-200 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded px-2 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-survivor-orange"
                      value={val}
                      onChange={e => handleChange(key, e.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {isDirty && (
        <p className="text-xs text-amber-600">
          ⚠ You have unsaved changes. Click "Save Config" to persist them.
        </p>
      )}
    </div>
  )
}

// ── Castaways Tab ─────────────────────────────────────────────────────────────

function CastawayRow({ castaway }: { castaway: AdminCastaway }) {
  const updateAlias = useUpdateCastawayAlias()
  const [alias, setAlias] = useState(castaway.alias)
  const [msg, setMsg] = useState('')
  const dirty = alias !== castaway.alias

  async function handleSave(refetch: boolean) {
    setMsg('')
    try {
      await updateAlias.mutateAsync({ castaway_id: castaway.castaway_id, alias, refetch_image: refetch })
      setMsg(refetch ? 'Saved & image re-fetched.' : 'Saved.')
      setTimeout(() => setMsg(''), 3000)
    } catch {
      setMsg('Save failed.')
    }
  }

  return (
    <tr className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 align-top">
      {/* Image */}
      <td className="px-3 py-2 w-14">
        {castaway.image_url ? (
          <img
            src={castaway.image_url}
            alt={castaway.display_name}
            referrerPolicy="no-referrer"
            className="w-10 h-10 rounded-full object-cover object-top"
          />
        ) : (
          <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-400 text-xs">?</div>
        )}
      </td>
      {/* Dataset name */}
      <td className="px-3 py-2 text-sm font-medium">
        {castaway.name}
        {castaway.is_eliminated && <span className="ml-1 text-xs text-red-400">(out)</span>}
      </td>
      {/* Tribe */}
      <td className="px-3 py-2">
        {castaway.original_tribe && (
          <span
            className="inline-block text-xs font-medium px-2 py-0.5 rounded-full text-white whitespace-nowrap"
            style={{ backgroundColor: castaway.tribe_color || '#888' }}
          >
            {castaway.original_tribe}
          </span>
        )}
      </td>
      {/* Alias input */}
      <td className="px-3 py-2">
        <input
          className="input text-sm py-1"
          placeholder="Same as dataset name"
          value={alias}
          onChange={e => { setAlias(e.target.value); setMsg('') }}
        />
      </td>
      {/* Actions */}
      <td className="px-3 py-2">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            className="btn-primary text-xs px-2 py-1"
            onClick={() => handleSave(false)}
            disabled={!dirty || updateAlias.isPending}
          >
            Save
          </button>
          <button
            className="btn-secondary text-xs px-2 py-1"
            onClick={() => handleSave(true)}
            disabled={updateAlias.isPending}
            title="Save alias and re-fetch image from Fandom"
          >
            Save & Re-fetch Image
          </button>
          {msg && (
            <span className={`text-xs ${msg.includes('failed') ? 'text-red-500' : 'text-green-600'}`}>
              {msg}
            </span>
          )}
        </div>
      </td>
    </tr>
  )
}

function CastawaysTab() {
  const { data: activeSeasonData } = useActiveSeason()
  const ACTIVE_SEASON = activeSeasonData?.season?.season_number ?? 0
  const { data: castaways, isLoading } = useAdminCastaways(ACTIVE_SEASON)
  const [filter, setFilter] = useState('')

  const filtered = castaways?.filter(c =>
    c.name.toLowerCase().includes(filter.toLowerCase()) ||
    c.alias.toLowerCase().includes(filter.toLowerCase())
  ) ?? []

  return (
    <div>
      <div className="card mb-4 flex items-center gap-4">
        <div className="flex-1">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Set an <strong>alias</strong> for any castaway whose legal name differs from their Fandom wiki page name.
            The alias is used as their display name site-wide and for image lookups.
            Use <em>Save & Re-fetch Image</em> after setting an alias to pull the correct photo.
          </p>
        </div>
      </div>

      <div className="mb-4">
        <input
          className="input max-w-xs"
          placeholder="Filter by name or alias…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />
      </div>

      <div className="card overflow-hidden p-0">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <h2 className="font-semibold">
            Season {ACTIVE_SEASON} Castaways
            <span className="ml-2 text-xs font-normal text-gray-400 dark:text-gray-500">
              ({filtered.length} shown)
            </span>
          </h2>
        </div>
        {isLoading ? (
          <div className="p-4 text-gray-400 dark:text-gray-500">Loading…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-2">Photo</th>
                  <th className="px-3 py-2">Dataset Name</th>
                  <th className="px-3 py-2">Tribe</th>
                  <th className="px-3 py-2">Alias (display name override)</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {filtered.map(c => (
                  <CastawayRow key={c.castaway_id} castaway={c} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
