import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateLeague } from '../api/leagues'

export default function CreateLeaguePage() {
  const [name, setName] = useState('')
  const [created, setCreated] = useState<{ slug: string; invite_code: string } | null>(null)
  const createLeague = useCreateLeague()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const league = await createLeague.mutateAsync(name)
    setCreated({ slug: league.slug, invite_code: league.invite_code ?? '' })
  }

  if (created) {
    return (
      <div className="max-w-md mx-auto card text-center py-10">
        <h2 className="text-xl font-bold mb-2">League Created!</h2>
        <p className="text-gray-500 mb-6">Share this invite code with your players:</p>
        <div className="bg-gray-100 rounded-xl px-6 py-4 text-3xl font-mono font-bold tracking-widest text-survivor-orange mb-6">
          {created.invite_code}
        </div>
        <button onClick={() => navigate(`/leagues/${created.slug}`)} className="btn-primary w-full">
          Go to League
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-6">Create a League</h1>
      <form onSubmit={handleSubmit} className="card flex flex-col gap-4">
        <div>
          <label className="label">League Name</label>
          <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="My Survivor Pool" required />
        </div>
        <button type="submit" className="btn-primary" disabled={createLeague.isPending}>
          {createLeague.isPending ? 'Creating…' : 'Create League'}
        </button>
        {createLeague.isError && <p className="text-red-500 text-sm">Failed to create league.</p>}
      </form>
    </div>
  )
}
