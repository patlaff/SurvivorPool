# Tasks: Perk Eligibility Controls

## Phase 1 — Backend

### 1.1 Model & migration
- [x] Add `is_merge` (BooleanField, default False) and `is_finale` (BooleanField, default False) to `Episode` in `apps/castaways/models.py`
- [x] Write migration `apps/castaways/migrations/0002_episode_perk_flags.py`

### 1.2 Sync: populate flags
- [x] In `apps/scoring/tasks.py` `_sync_season`, after episodes are upserted:
  - Load `tribe_mapping` JSON; find the minimum episode number where `tribe_status == 'Merged'` for the season; set `is_merge=True` on that episode, clear on all others
  - Load `episodes` JSON; find episodes where `episode_label == 'Finale'`; set `is_finale=True` on those, clear on all others

### 1.3 Episode serializer & endpoint
- [x] Add `is_merge` and `is_finale` to `EpisodeSerializer` in `apps/castaways/serializers.py`
- [x] Add `SeasonEpisodesView` (ListAPIView, IsAuthenticated) to `apps/castaways/views.py` — filters by `season__season_number` and `season__version='US'`, ordered by `episode_number`
- [x] Register `path('seasons/<int:season_number>/episodes/', SeasonEpisodesView.as_view(), name='season-episodes')` in `apps/castaways/urls.py`

### 1.4 Enforce swap eligibility
- [x] In `apps/leagues/views.py` `SwapPerkView.post`:
  - Replace the `lock_date` guard with `is_draft_open(league)` — return 400 if draft is still open
  - Add merge gate: query `Episode.objects.filter(season=league.season, is_merge=True).first()`; if found and `air_date <= today`, return 400 "Swap perk has expired — the tribes have merged."

### 1.5 Enforce boost eligibility
- [x] In `apps/leagues/views.py` `BoostPerkView.post`:
  - After the existing "already scored" check, add: if `episode.is_finale`, return 400 "Boost cannot be applied to the finale."

---

## Phase 2 — Frontend

### 2.1 API types & hook
- [x] Add `SeasonEpisode` interface to `frontend/src/api/leagues.ts`: `{ episode_number, air_date, scored_at, is_merge, is_finale }`
- [x] Add `useSeasonEpisodes(seasonNumber)` query hook: `GET /seasons/{seasonNumber}/episodes/`, `enabled: seasonNumber > 0`

### 2.2 RosterPage perk UI
- [x] Add `useLeague(slug!)` and `useSeasonEpisodes(league?.season_number ?? 0)` calls to `RosterPage`
- [x] Derive `swapWindowOpen`: true if no `is_merge` episode exists OR its `air_date` is in the future
- [x] Derive `boostEligible`: episodes that are not scored and not the finale
- [x] Swap card: when perk is unused and `!swapWindowOpen`, replace the "Use Swap" button with a muted "Window closed — tribes merged" note; keep form unchanged when `swapWindowOpen`
- [x] Boost card: replace the free-text episode number `<input>` with a `<select>` populated from `boostEligible`; if `boostEligible` is empty, show "No eligible episodes remaining"

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1.1 Model & migration | — |
| 1.2 Sync flags | 1.1 |
| 1.3 Serializer & endpoint | 1.1 |
| 1.4 Swap enforcement | 1.1 |
| 1.5 Boost enforcement | 1.1 |
| 2.1 API types & hook | 1.3 |
| 2.2 RosterPage UI | 2.1 |
