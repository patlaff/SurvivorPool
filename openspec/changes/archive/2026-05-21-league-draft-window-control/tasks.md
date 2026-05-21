# Tasks: League Draft Window Control

## Phase 1 — Backend

### 1.1 Model & migration
- [x] Add `draft_close_at` (DateTimeField, null/blank) and `draft_force_open` (BooleanField, default False) to `League` model in `apps/leagues/models.py`
- [x] Write migration `apps/leagues/migrations/0002_league_draft_window.py`

### 1.2 Shared utility
- [x] Create `apps/leagues/utils.py` with `is_draft_open(league) -> bool` implementing the 5-step resolution order from design.md

### 1.3 Update existing logic
- [x] Replace `LeagueSerializer.get_draft_open` to call `is_draft_open(obj)`
- [x] Replace `LeagueSerializer.get_draft_lock_date` to return `obj.draft_close_at` if set, else `obj.season.draft_lock_date`
- [x] Add `draft_close_at` and `draft_force_open` to `LeagueSerializer` and `LeagueDetailSerializer` fields
- [x] Replace the draft-open check in `DraftView.put` to call `is_draft_open(league)`

### 1.4 New endpoint
- [x] Add `DraftWindowView(APIView)` in `apps/leagues/views.py`:
  - `PATCH`: validate owner permission, accept `draft_close_at` (datetime or null) and `draft_force_open` (bool), save to league, return updated `LeagueDetailSerializer`
- [x] Register `path('leagues/<slug:slug>/draft-window/', DraftWindowView.as_view(), name='draft-window')` in `apps/leagues/urls.py`

---

## Phase 2 — Frontend

### 2.1 API types & hook
- [x] Extend `League` interface in `frontend/src/api/leagues.ts` with `draft_close_at: string | null` and `draft_force_open: boolean`
- [x] Add `useDraftWindow(slug)` mutation: `PATCH /leagues/{slug}/draft-window/` — on success invalidates `['league', slug]` and `['draft', slug]`

### 2.2 Draft Settings panel in LeaguePage
- [x] Add a "Draft Settings" card below the tab bar in `LeaguePage.tsx`, visible only when `user.id === league.owner.id`
- [x] Show status badge: green "Open" / red "Closed", with formatted `draft_close_at` timestamp if present
- [x] "Close draft now" button: calls `useDraftWindow` with `{ draft_close_at: new Date().toISOString(), draft_force_open: false }`
- [x] "Reopen draft" button: calls `useDraftWindow` with `{ draft_close_at: null, draft_force_open: true }`; always enabled — `Season.draft_lock_date` is only a default, not a hard ceiling
- [x] `<input type="datetime-local">` + "Set" button: sends chosen datetime as `draft_close_at`
- [x] "Revert to season default" button: sends `{ draft_close_at: null, draft_force_open: false }`
- [x] Display inline success/error feedback after each action (no full page reload)

---

## Implementation Order

| Task | Depends on |
|---|---|
| 1.1 Model & migration | — |
| 1.2 Utility | 1.1 |
| 1.3 Update existing logic | 1.2 |
| 1.4 New endpoint | 1.2, 1.3 |
| 2.1 API types & hook | 1.4 |
| 2.2 Draft Settings panel | 2.1 |
