import { useQuery } from '@tanstack/react-query'
import { api } from './client'

export interface SeasonInfo {
  season_number: number
  name: string
  is_active: boolean
  draft_lock_date: string | null
  allows_new_leagues: boolean
  next_detected_at: string | null
}

export interface EpisodeInfo {
  episode_number: number
  air_date: string
  scored_at: string | null
  is_merge: boolean
  is_finale: boolean
}

export interface ActiveSeasonResponse {
  season: SeasonInfo
  episodes: EpisodeInfo[]
}

export function useActiveSeason() {
  return useQuery<ActiveSeasonResponse>({
    queryKey: ['active-season'],
    queryFn: () => api.get('/active-season/').then(r => r.data),
  })
}

export function usePublicScoringConfig() {
  return useQuery<{ config: Record<string, number> }>({
    queryKey: ['public-scoring-config'],
    queryFn: () => api.get('/scoring-config/').then(r => r.data),
  })
}
