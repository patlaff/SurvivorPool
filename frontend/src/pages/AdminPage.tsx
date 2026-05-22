import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  useAdminLeagues,
  useCreateTestLeague,
  useScoringConfig,
  useSaveConfig,
  useRescoreSeason,
  useScoreUnscored,
  useScoringSummary,
} from '../api/admin'

type Tab = 'leagues' | 'scoring' | 'config'

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

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {(['leagues', 'scoring', 'config'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              tab === t
                ? 'border-survivor-orange text-survivor-orange'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'leagues' ? 'Leagues' : t === 'scoring' ? 'Scoring Summary' : 'Scoring Config'}
          </button>
        ))}
      </div>

      {tab === 'leagues' && <LeaguesTab />}
      {tab === 'scoring' && <ScoringTab />}
      {tab === 'config' && <ConfigTab />}
    </div>
  )
}

// ── Leagues Tab ───────────────────────────────────────────────────────────────

function LeaguesTab() {
  const { data: leagues, isLoading } = useAdminLeagues()
  const createTestLeague = useCreateTestLeague()
  const [newName, setNewName] = useState('')
  const [created, setCreated] = useState<{ slug: string; invite_code: string; name: string } | null>(null)
  const [error, setError] = useState('')

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setCreated(null)
    try {
      const result = await createTestLeague.mutateAsync(newName)
      setCreated({ slug: result.slug, invite_code: result.invite_code, name: result.name })
      setNewName('')
    } catch {
      setError('Failed to create test league.')
    }
  }

  return (
    <div>
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
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
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

      {/* All leagues table */}
      <div className="card overflow-hidden p-0">
        <div className="px-4 py-3 border-b border-gray-100">
          <h2 className="font-semibold">All Leagues ({leagues?.length ?? 0})</h2>
        </div>
        {isLoading ? (
          <div className="p-4 text-gray-400">Loading...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wider">
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
              <tbody className="divide-y divide-gray-100">
                {leagues?.map(league => (
                  <tr key={league.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <Link to={`/leagues/${league.slug}`} className="text-survivor-orange hover:underline font-medium">
                        {league.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      <div className="font-medium">{league.owner.display_name}</div>
                      <div className="text-gray-400 text-xs">{league.owner.email}</div>
                    </td>
                    <td className="px-4 py-2 text-center">{league.member_count}</td>
                    <td className="px-4 py-2">
                      {league.draft_open
                        ? <span className="badge-green">Open</span>
                        : <span className="badge-gray">Closed</span>}
                    </td>
                    <td className="px-4 py-2">
                      {league.is_test && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-orange-100 text-orange-800">
                          TEST
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{league.invite_code}</td>
                    <td className="px-4 py-2 text-gray-500 text-xs">
                      {new Date(league.created_at).toLocaleDateString()}
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

// ── Scoring Summary Tab ───────────────────────────────────────────────────────

const ACTIVE_SEASON = 50

function ScoringTab() {
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

  if (isLoading) return <div className="text-gray-400">Loading scoring data...</div>

  return (
    <div>
      {/* Score unscored episodes */}
      <div className="card mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-semibold">Score Past Episodes</h2>
          <p className="text-sm text-gray-500 mt-0.5">
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
          disabled={scoreUnscored.isPending}
        >
          {scoreUnscored.isPending ? 'Scoring…' : 'Score All Unscored'}
        </button>
      </div>

      {/* Castaway totals */}
      <div className="card mb-6">
        <h2 className="font-semibold mb-3">
          Castaway Totals — Season {data?.season_number ?? ACTIVE_SEASON}
          <span className="ml-2 text-xs text-gray-400 font-normal">
            ({data?.scored_episodes.length ?? 0} episodes scored)
          </span>
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2">Rank</th>
                <th className="px-3 py-2">Castaway</th>
                <th className="px-3 py-2 text-right">Total Pts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(data?.castaway_totals ?? []).map((c, i) => (
                <tr key={c.castaway_id} className="hover:bg-gray-50">
                  <td className="px-3 py-1.5 text-gray-400">{i + 1}</td>
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
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
              onClick={() => setOpenEpisode(openEpisode === ep.episode_number ? null : ep.episode_number)}
            >
              <span className="font-medium">
                Episode {ep.episode_number}
                <span className="ml-2 text-sm text-gray-400">{ep.air_date}</span>
              </span>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span>{ep.events.length} events</span>
                <span className="font-semibold text-gray-700">{ep.episode_total} pts total</span>
                <span>{openEpisode === ep.episode_number ? '▲' : '▼'}</span>
              </div>
            </button>
            {openEpisode === ep.episode_number && (
              <div className="border-t border-gray-100 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-2 text-left">Castaway</th>
                      <th className="px-4 py-2 text-left">Event</th>
                      <th className="px-4 py-2 text-right">Pts</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {ep.events.map((ev, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-1.5 font-medium">{ev.castaway_name}</td>
                        <td className="px-4 py-1.5 font-mono text-xs text-gray-600">
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
        <p className="text-gray-400 text-sm">No episodes have been scored yet.</p>
      )}
    </div>
  )
}

// ── Scoring Config Tab ────────────────────────────────────────────────────────

function ConfigTab() {
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

  if (isLoading) return <div className="text-gray-400">Loading config...</div>

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
              disabled={rescoreSeason.isPending}
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
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2 text-left">Event</th>
                <th className="px-3 py-2 text-right w-32">Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {Object.entries(config).sort(([a], [b]) => a.localeCompare(b)).map(([key, val]) => (
                <tr key={key} className="hover:bg-gray-50">
                  <td className="px-3 py-1.5 font-mono text-xs">{key}</td>
                  <td className="px-3 py-1.5 text-right">
                    <input
                      type="number"
                      className="w-20 text-right border border-gray-200 rounded px-2 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-survivor-orange"
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
