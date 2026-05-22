import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

export interface AdminLeague {
  id: number
  name: string
  slug: string
  owner: { id: number; display_name: string; email: string }
  member_count: number
  is_test: boolean
  invite_code: string
  draft_open: boolean
  created_at: string
}

export interface ScoringEvent {
  castaway_id: string
  castaway_name: string
  event_name: string
  points: number
}

export interface ScoredEpisode {
  episode_number: number
  air_date: string
  scored_at: string | null
  events: ScoringEvent[]
  episode_total: number
}

export interface CastawayTotal {
  castaway_id: string
  name: string
  total_points: number
  is_eliminated: boolean
}

export interface ScoringSummary {
  season_number: number
  scored_episodes: ScoredEpisode[]
  castaway_totals: CastawayTotal[]
}

export interface ScoringConfig {
  config: Record<string, number>
}

export interface RescoreResult {
  episodes_rescored: number
  rosters_updated: number
}

export interface ScoreUnscoredResult {
  episodes_attempted: number
  episodes_scored: number
  episodes: { episode_number: number; status: 'scored' | 'skipped' | 'error'; reason?: string }[]
}

export function useAdminLeagues() {
  return useQuery<AdminLeague[]>({
    queryKey: ['admin-leagues'],
    queryFn: () => api.get('/admin/leagues/').then(r => r.data),
  })
}

export function useCreateTestLeague() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.post('/admin/leagues/', { name }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-leagues'] }),
  })
}

export function useScoringConfig() {
  return useQuery<ScoringConfig>({
    queryKey: ['admin-scoring-config'],
    queryFn: () => api.get('/admin/scoring-config/').then(r => r.data),
  })
}

export function useSaveConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: Record<string, number>) =>
      api.put('/admin/scoring-config/', { config }).then(r => r.data as ScoringConfig),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-scoring-config'] }),
  })
}

export function useRescoreSeason() {
  return useMutation({
    mutationFn: (seasonNumber: number) =>
      api.post(`/admin/rescore/${seasonNumber}/`).then(r => r.data as RescoreResult),
  })
}

export function useScoreUnscored() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (seasonNumber: number) =>
      api.post(`/admin/score-unscored/${seasonNumber}/`).then(r => r.data as ScoreUnscoredResult),
    onSuccess: (_, seasonNumber) => {
      // Invalidate the scoring summary so it refreshes after new episodes are scored
      qc.invalidateQueries({ queryKey: ['admin-scoring-summary', seasonNumber] })
    },
  })
}

export function useScoringSummary(seasonNumber: number) {
  return useQuery<ScoringSummary>({
    queryKey: ['admin-scoring-summary', seasonNumber],
    queryFn: () => api.get(`/admin/seasons/${seasonNumber}/scoring-summary/`).then(r => r.data),
    enabled: seasonNumber > 0,
  })
}
