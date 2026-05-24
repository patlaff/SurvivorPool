import { useActiveSeason, usePublicScoringConfig } from '../api/info'

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  })
}

function formatEventName(key: string) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

export default function InfoPage() {
  const { data: seasonData, isLoading: seasonLoading } = useActiveSeason()
  const { data: configData, isLoading: configLoading } = usePublicScoringConfig()

  const season = seasonData?.season
  const episodes = seasonData?.episodes ?? []
  const config = configData?.config ?? {}

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  return (
    <div className="max-w-4xl space-y-10">

      {/* ── How to Play ──────────────────────────────────────────────────── */}
      <section>
        <h1 className="text-3xl font-bold mb-1">How to Play</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">Everything you need to know about SurvivorPool</p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="card">
            <h2 className="font-semibold text-lg mb-2">🏝 Pick Your Tribe</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Before the draft closes, pick <strong>5 castaways</strong> from the current Survivor season.
              These players make up your personal roster for the entire season.
            </p>
          </div>
          <div className="card">
            <h2 className="font-semibold text-lg mb-2">📺 Earn Points Each Episode</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              After each episode airs, points are automatically tallied based on what your castaways did —
              winning challenges, finding idols, getting votes, and more.
            </p>
          </div>
          <div className="card">
            <h2 className="font-semibold text-lg mb-2">🔄 Swap Perk</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Once per season, use your <strong>Swap</strong> perk to replace one castaway on your roster
              with any available player. Available after the merge episode.
            </p>
          </div>
          <div className="card">
            <h2 className="font-semibold text-lg mb-2">⚡ Boost Perk</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Once per season, use your <strong>Boost</strong> perk to double all points earned by your
              roster for a chosen episode. Pick wisely — it can only be used before the episode airs.
            </p>
          </div>
          <div className="card sm:col-span-2">
            <h2 className="font-semibold text-lg mb-2">🏆 Win Your League</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              The player with the most cumulative points at the end of the season wins the league.
              Scores update automatically after each episode is processed. Rally your alliance and
              outlast, outplay, outwit!
            </p>
          </div>
          <div className="card sm:col-span-2">
            <h2 className="font-semibold text-lg mb-2">💸 Buy-ins (Optional)</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              League owners can optionally set a monetary buy-in and share a Venmo handle to collect
              payments. If your league has a buy-in, you'll see the amount and Venmo handle at the
              top of the league page.
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
              Buy-ins are not required — not every league will have one. Payment and buy-in tracking
              is handled manually by the league owner outside the app: once you've paid, the owner
              will mark you as bought in on their end.
            </p>
          </div>
        </div>
      </section>

      {/* ── Points Breakdown ─────────────────────────────────────────────── */}
      <section>
        <h2 className="text-2xl font-bold mb-1">Points Breakdown</h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">How points are awarded each episode</p>

        {configLoading ? (
          <div className="text-gray-400 dark:text-gray-500 text-sm">Loading scoring info…</div>
        ) : Object.keys(config).length === 0 ? (
          <div className="text-gray-400 dark:text-gray-500 text-sm">No scoring data available.</div>
        ) : (
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">Event</th>
                  <th className="px-4 py-3 text-right w-28">Points</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {Object.entries(config)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([key, pts]) => (
                    <tr key={key} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
                        {formatEventName(key)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span className={`font-semibold ${pts > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                          {pts > 0 ? `+${pts}` : pts}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Season Schedule ──────────────────────────────────────────────── */}
      <section>
        <h2 className="text-2xl font-bold mb-1">
          {season ? `Season ${season.season_number} — ${season.name}` : 'Current Season'}
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">Episode schedule and scoring status</p>

        {seasonLoading ? (
          <div className="text-gray-400 dark:text-gray-500 text-sm">Loading season info…</div>
        ) : episodes.length === 0 ? (
          <div className="text-gray-400 dark:text-gray-500 text-sm">No episode data available.</div>
        ) : (
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">Episode</th>
                  <th className="px-4 py-3 text-left">Air Date</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {episodes.map(ep => {
                  const airDate = new Date(ep.air_date)
                  airDate.setHours(0, 0, 0, 0)
                  const hasAired = airDate <= today
                  const isScored = !!ep.scored_at
                  const isUpcoming = !hasAired

                  return (
                    <tr
                      key={ep.episode_number}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 ${isUpcoming ? 'text-gray-400 dark:text-gray-500' : ''}`}
                    >
                      <td className="px-4 py-2 font-medium">
                        Ep {ep.episode_number}
                      </td>
                      <td className="px-4 py-2">
                        {formatDate(ep.air_date)}
                      </td>
                      <td className="px-4 py-2">
                        {ep.is_finale ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-purple-700 bg-purple-100 px-2 py-0.5 rounded-full">
                            🏆 Finale
                          </span>
                        ) : ep.is_merge ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                            🤝 Merge
                          </span>
                        ) : (
                          <span className="text-gray-400 dark:text-gray-500 text-xs">Regular</span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        {isScored ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                            ✓ Scored
                          </span>
                        ) : hasAired ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-yellow-700 bg-yellow-100 px-2 py-0.5 rounded-full">
                            ⏳ Pending
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400 dark:text-gray-500">Upcoming</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {season?.draft_lock_date && (
              <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50">
                Draft closes: <strong>{formatDate(season.draft_lock_date)}</strong>
              </div>
            )}
          </div>
        )}
      </section>

    </div>
  )
}
