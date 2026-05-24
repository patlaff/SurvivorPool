import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

export interface League {
  id: number
  name: string
  slug: string
  season_id: number
  season_number: number
  owner: { id: number; display_name: string; avatar_url: string }
  member_count: number
  draft_lock_date: string | null
  draft_open: boolean
  draft_close_at: string | null
  draft_force_open: boolean
  is_test: boolean
  is_archived: boolean
  created_at: string
  buy_in_amount: string | null
  venmo_handle: string | null
  invite_code?: string
  members?: { user: { id: number; display_name: string; avatar_url: string }; joined_at: string; bought_in: boolean }[]
}

export interface LeagueOverviewMember {
  user: { id: number; display_name: string; avatar_url: string }
  joined_at: string
  pick_count: number
  bought_in: boolean
}

export interface LeagueOverviewResponse {
  members: LeagueOverviewMember[]
}

export interface Castaway {
  castaway_id: string
  name: string
  alias: string
  display_name: string
  age: number | null
  hometown: string
  occupation: string
  image_url: string
  original_tribe: string
  tribe_color: string
  is_eliminated: boolean
  eliminated_episode: number | null
}

export interface EpisodeScore {
  episode_number: number
  air_date: string
  raw_points: number
  multiplier: string
  final_points: number
}

export interface LeaderboardEntry {
  rank: number
  user: { id: number; display_name: string; avatar_url: string }
  total_points: number
  episodes: EpisodeScore[]
  /** True when the draft is open and this entry belongs to another player. */
  roster_hidden: boolean
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[]
  last_scored_at: string | null
  /** Whether the draft window is currently open for this league. */
  draft_open: boolean
}

export interface RosterSlot {
  slot_number: number
  castaway: Castaway
  added_at: string
  events: { castaway_name: string; event_name: string; points: number }[]
}

export interface Perk {
  perk_type: 'swap' | 'boost'
  used: boolean
  used_at: string | null
  boost_target_episode: number | null
  swapped_out_castaway: Castaway | null
  swapped_in_castaway: Castaway | null
}

export interface Roster {
  id: number
  user: { id: number; display_name: string; avatar_url: string }
  slots: RosterSlot[]
  perks: Perk[]
  total_points: number
}

export function useMyLeagues(userId?: number) {
  return useQuery<League[]>({
    queryKey: ['leagues', userId],
    queryFn: () => api.get('/leagues/').then(r => r.data),
    enabled: !!userId,
  })
}

export function useLeague(slug: string, userId?: number) {
  return useQuery<League>({
    queryKey: ['league', slug, userId],
    queryFn: () => api.get(`/leagues/${slug}/`).then(r => r.data),
    enabled: !!userId,
    // Poll every 30 s so draft-open state and other league settings propagate
    // to all members without requiring a manual page refresh.
    refetchInterval: 30_000,
  })
}

export function useLeaderboard(slug: string) {
  return useQuery<LeaderboardResponse>({
    queryKey: ['leaderboard', slug],
    queryFn: () => api.get(`/leagues/${slug}/leaderboard/`).then(r => r.data),
    refetchInterval: 1000 * 60 * 5,
  })
}

export function useAvailableCastaways(slug: string) {
  return useQuery<Castaway[]>({
    queryKey: ['available-castaways', slug],
    queryFn: () => api.get(`/leagues/${slug}/available-castaways/`).then(r => r.data),
  })
}

export function useSeasonCastaways(seasonNumber: number) {
  return useQuery<Castaway[]>({
    queryKey: ['season-castaways', seasonNumber],
    queryFn: () => api.get(`/seasons/${seasonNumber}/castaways/`).then(r => r.data),
  })
}

export interface SeasonEpisode {
  episode_number: number
  air_date: string
  scored_at: string | null
  is_merge: boolean
  is_finale: boolean
}

export function useSeasonEpisodes(seasonNumber: number) {
  return useQuery<SeasonEpisode[]>({
    queryKey: ['season-episodes', seasonNumber],
    queryFn: () => api.get(`/seasons/${seasonNumber}/episodes/`).then(r => r.data),
    enabled: seasonNumber > 0,
  })
}

export function useDraft(slug: string, userId?: number) {
  return useQuery<{ draft_open: boolean; lock_date: string | null; picks: string[] }>({
    queryKey: ['draft', slug, userId],
    queryFn: () => api.get(`/leagues/${slug}/draft/`).then(r => r.data),
    enabled: !!userId,
    // Poll every 30 s so the draft-open state stays in sync across users
    // (e.g. when the league owner reopens the draft while another member has
    // the page open).
    refetchInterval: 30_000,
  })
}

export function useMyRoster(slug: string, userId?: number) {
  return useQuery<Roster>({
    queryKey: ['roster', slug, 'me', userId],
    queryFn: () => api.get(`/leagues/${slug}/roster/`).then(r => r.data),
    enabled: !!userId,
  })
}

export function useMemberRoster(slug: string, userId: number) {
  return useQuery<Roster>({ queryKey: ['roster', slug, userId], queryFn: () => api.get(`/leagues/${slug}/roster/${userId}/`).then(r => r.data) })
}

export function useMyScores(slug: string) {
  return useQuery<EpisodeScore[]>({ queryKey: ['scores', slug], queryFn: () => api.get(`/leagues/${slug}/scores/`).then(r => r.data) })
}

export function useCreateLeague() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.post('/leagues/', { name }).then(r => r.data as League),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leagues'] }),
  })
}

export function useJoinLeague() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ invite_code }: { invite_code: string }) =>
      api.post('/leagues/join/', { invite_code }).then(r => r.data as { detail: string; slug: string }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leagues'] }),
  })
}

export function useSaveDraft(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (castaway_ids: string[]) => api.put(`/leagues/${slug}/draft/`, { castaway_ids }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['draft', slug] })
      qc.invalidateQueries({ queryKey: ['available-castaways', slug] })
      // Invalidate roster so total_points reflects newly-computed episode scores
      qc.invalidateQueries({ queryKey: ['roster', slug] })
      qc.invalidateQueries({ queryKey: ['leaderboard', slug] })
    },
  })
}

export function useSwapPerk(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ out_id, in_id }: { out_id: string; in_id: string }) =>
      api.post(`/leagues/${slug}/roster/swap/`, { out_id, in_id }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['roster', slug, 'me'] }),
  })
}

export function useBoostPerk(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (episode_number: number) =>
      api.post(`/leagues/${slug}/roster/boost/`, { episode_number }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['roster', slug, 'me'] }),
  })
}

export interface DraftWindowPayload {
  draft_close_at?: string | null
  draft_force_open?: boolean
}

export function useDraftWindow(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: DraftWindowPayload) =>
      api.patch(`/leagues/${slug}/draft-window/`, payload).then(r => r.data as League),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['league', slug] })
      qc.invalidateQueries({ queryKey: ['draft', slug] })
    },
  })
}

export interface PicksGridCastaway {
  castaway_id: string
  name: string
  original_tribe: string
  tribe_color: string
  is_eliminated: boolean
  eliminated_episode: number | null
  pick_count: number
  total_points: number
}

export interface PicksGridPlayer {
  user: { id: number; display_name: string; avatar_url: string }
  picks: string[]
  has_drafted: boolean
}

export interface PicksGridResponse {
  draft_open: boolean
  players: PicksGridPlayer[]
  castaways: PicksGridCastaway[]
}

export function usePicksGrid(slug: string) {
  return useQuery<PicksGridResponse>({
    queryKey: ['picks-grid', slug],
    queryFn: () => api.get(`/leagues/${slug}/picks-grid/`).then(r => r.data),
    refetchInterval: 1000 * 60 * 5,
  })
}

export interface ActivityEvent {
  type: 'draft_saved' | 'swap_used' | 'boost_used'
  timestamp: string
  user: { id: number; display_name: string; avatar_url: string }
  detail: Record<string, unknown>
}

export function useLeagueActivity(slug: string, enabled: boolean) {
  return useQuery<ActivityEvent[]>({
    queryKey: ['league-activity', slug],
    queryFn: () => api.get(`/leagues/${slug}/activity/`).then(r => r.data),
    enabled,
  })
}

export function useLeagueOverview(slug: string, enabled: boolean) {
  return useQuery<LeagueOverviewResponse>({
    queryKey: ['league-overview', slug],
    queryFn: () => api.get(`/leagues/${slug}/overview/`).then(r => r.data),
    enabled,
  })
}

export interface LeagueSettingsPayload {
  buy_in_amount?: string | null
  venmo_handle?: string | null
}

export function useUpdateLeagueSettings(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: LeagueSettingsPayload) =>
      api.patch(`/leagues/${slug}/`, payload).then(r => r.data as League),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['league', slug] }),
  })
}

export function useToggleMemberBuyIn(slug: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, bought_in }: { userId: number; bought_in: boolean }) =>
      api.patch(`/leagues/${slug}/members/${userId}/buy-in/`, { bought_in }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['league-overview', slug] }),
  })
}
