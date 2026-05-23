import { useState } from 'react'
import { Link } from 'react-router-dom'
import { League, useMyLeagues, useCreateLeague, useJoinLeague } from '../api/leagues'
import { useActiveSeason } from '../api/info'
import { useAuth } from '../hooks/useAuth'
export default function DashboardPage() {
  const { user } = useAuth()
  const { data: leagues, isLoading } = useMyLeagues(user?.id)
  const { data: activeSeasonData } = useActiveSeason()
  const canCreateLeague = activeSeasonData?.season?.allows_new_leagues ?? false
  const createLeague = useCreateLeague()
  const joinLeague = useJoinLeague()

  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [showJoin, setShowJoin] = useState(false)
  const [joinCode, setJoinCode] = useState('')
  const [error, setError] = useState('')

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await createLeague.mutateAsync(newName)
      setNewName('')
      setShowCreate(false)
    } catch {
      setError('Failed to create league.')
    }
  }

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await joinLeague.mutateAsync({ invite_code: joinCode })
      setJoinCode('')
      setShowJoin(false)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { retry_after?: number } } }
      if (axiosErr.response?.status === 429) {
        const secs = axiosErr.response.data?.retry_after ?? 30
        setError(`Too many failed attempts. Try again in ${secs}s.`)
      } else {
        setError('Invalid invite code.')
      }
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Leagues</h1>
        <div className="flex gap-3">
          {canCreateLeague && (
            <button onClick={() => setShowJoin(true)} className="btn-secondary">Join League</button>
          )}
          {canCreateLeague && (
            <button onClick={() => setShowCreate(true)} className="btn-primary">+ New League</button>
          )}
        </div>
      </div>

      {error && <p className="text-red-500 mb-4">{error}</p>}

      {canCreateLeague && showCreate && (
        <form onSubmit={handleCreate} className="card mb-6 flex gap-3 items-end">
          <div className="flex-1">
            <label className="label">League Name</label>
            <input className="input" value={newName} onChange={e => setNewName(e.target.value)} placeholder="My Survivor Pool" required />
          </div>
          <button type="submit" className="btn-primary" disabled={createLeague.isPending}>Create</button>
          <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
        </form>
      )}

      {canCreateLeague && showJoin && (
        <form onSubmit={handleJoin} className="card mb-6 flex gap-3 items-end">
          <div className="flex-1">
            <label className="label">Invite Code</label>
            <input className="input" value={joinCode} onChange={e => setJoinCode(e.target.value)} placeholder="ABCD1234" required />
          </div>
          <button type="submit" className="btn-primary" disabled={joinLeague.isPending}>Join</button>
          <button type="button" onClick={() => setShowJoin(false)} className="btn-secondary">Cancel</button>
        </form>
      )}

      {isLoading && <div className="text-gray-400 dark:text-gray-500">Loading...</div>}

      {leagues?.length === 0 && (
        <div className="card text-center py-16 text-gray-400 dark:text-gray-500">
          <p className="text-lg">You haven't joined any leagues yet.</p>
          <p className="text-sm mt-1">Create one or ask a friend for an invite code.</p>
        </div>
      )}

      {/* Active leagues */}
      <ActiveLeaguesGrid leagues={leagues?.filter(l => !l.is_archived) ?? []} />

      {/* Archived leagues — collapsible */}
      <ArchivedLeaguesSection leagues={leagues?.filter(l => l.is_archived) ?? []} />
    </div>
  )
}

function ActiveLeaguesGrid({ leagues }: { leagues: League[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {leagues.map(league => (
        <Link key={league.slug} to={`/leagues/${league.slug}`} className="card hover:border-survivor-orange transition-colors">
          <h2 className="font-semibold text-lg">{league.name}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{league.member_count} player{league.member_count !== 1 ? 's' : ''}</p>
          <div className="mt-3 flex gap-2 text-sm">
            {league.draft_open
              ? <span className="badge-green">Draft open</span>
              : <span className="badge-gray">Draft closed</span>}
          </div>
        </Link>
      ))}
    </div>
  )
}

function ArchivedLeaguesSection({ leagues }: { leagues: League[] }) {
  const [showArchived, setShowArchived] = useState(false)

  if (leagues.length === 0) return null

  return (
    <div className="mt-8">
      <button
        className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors mb-4"
        onClick={() => setShowArchived(v => !v)}
      >
        <span>Past Seasons ({leagues.length})</span>
        <span className="text-xs">{showArchived ? '▲' : '▼'}</span>
      </button>
      {showArchived && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {leagues.map(league => (
            <Link key={league.slug} to={`/leagues/${league.slug}`} className="card opacity-70 hover:opacity-100 transition-opacity">
              <h2 className="font-semibold text-lg text-gray-600 dark:text-gray-400">{league.name}</h2>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{league.member_count} player{league.member_count !== 1 ? 's' : ''}</p>
              <div className="mt-3 flex gap-2 text-sm">
                <span className="badge-gray">Archived</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
