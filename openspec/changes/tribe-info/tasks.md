# Tasks: Tribe Info on Castaways

## Task 1 — Add `original_tribe` and `tribe_color` to `Castaway` model

**File:** `backend/apps/castaways/models.py`

- [x] Add `original_tribe = models.CharField(max_length=100, blank=True)` to `Castaway`
- [x] Add `tribe_color = models.CharField(max_length=10, blank=True)` to `Castaway`
- [x] Inside the backend container, run:
  ```
  python manage.py makemigrations castaways
  python manage.py migrate
  ```
- [x] Copy the generated migration file back to the host

Test: `Castaway.objects.first().original_tribe` and `.tribe_color` exist without error.

---

## Task 2 — Update sync task to populate tribe fields

**File:** `backend/apps/scoring/tasks.py`

- [x] After loading `castaways.json` in `_sync_season`, fetch `tribe_colours.json` and build `tribe_color_map: dict[str, str]` mapping original-tribe names to hex colors (filter `tribe_status == "Original"`, wrap in `try/except`):
  ```python
  tribe_color_map: dict[str, str] = {}
  try:
      tc = _fetch_json('tribe_colours')
      us_tc = _filter_us_season(tc, season_number)
      original_tribes = us_tc[us_tc['tribe_status'] == 'Original']
      tribe_color_map = dict(zip(original_tribes['tribe'], original_tribes['tribe_colour']))
  except Exception:
      logger.debug('tribe_colours unavailable — tribe colors will be blank')
  ```
- [x] In the `update_or_create` loop, extract `original_tribe_val = str(row.get('original_tribe') or '').strip()` and add `'original_tribe': original_tribe_val` and `'tribe_color': tribe_color_map.get(original_tribe_val, '')` to `defaults`
- [x] Hot-patch + restart backend, then re-run `sync_season` for the active season:
  ```
  docker compose exec backend python manage.py sync_season <number>
  ```

Test: `Castaway.objects.filter(season__season_number=<N>).values('name','original_tribe','tribe_color')` returns populated tribe names and hex colors.

---

## Task 3 — Expose tribe fields in `CastawaySerializer`

**File:** `backend/apps/castaways/serializers.py`

- [x] Add `'original_tribe'` and `'tribe_color'` to `CastawaySerializer.Meta.fields`

Test: `GET /api/v1/seasons/<N>/castaways/` response includes `original_tribe` and `tribe_color` on each entry.

---

## Task 4 — Update TypeScript `Castaway` interface

**File:** `frontend/src/api/leagues.ts`

- [x] Add `original_tribe: string` and `tribe_color: string` to the `Castaway` interface

---

## Task 5 — Tribe badge on Draft page castaway cards

**File:** `frontend/src/pages/DraftPage.tsx`

- [x] Below the occupation line (`{c.occupation && ...}`), add a tribe badge when `c.original_tribe` is non-empty:
  ```tsx
  {c.original_tribe && (
    <span
      className="inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full text-white"
      style={{ backgroundColor: c.tribe_color || '#888' }}
    >
      {c.original_tribe}
    </span>
  )}
  ```

Test: Each castaway card shows a colored pill with the tribe name. Cards for eliminated/active castaways all show the badge.

---

## Task 6 — Color-code castaway names in picks grid

**File:** `frontend/src/pages/LeaguePage.tsx`

- [x] In the `PicksGridTab` component, update the castaway name `<span>` to apply `tribe_color` as an inline `color` style when the castaway is not eliminated:
  ```tsx
  <span
    className={castaway.is_eliminated ? 'line-through text-gray-400' : 'font-medium'}
    style={!castaway.is_eliminated && castaway.tribe_color ? { color: castaway.tribe_color } : undefined}
  >
    {castaway.name}
  </span>
  ```

Test: Picks grid castaway names are colored by tribe; eliminated castaways retain gray strikethrough with no tribe color.

---

## Task 7 — Rebuild and redeploy frontend

- [x] `docker compose build frontend && docker compose up -d frontend`

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — Model + migration | — |
| 2 — Sync task | 1 |
| 3 — Serializer | 1 |
| 4 — TS types | — |
| 5 — Draft page badge | 3, 4 |
| 6 — Picks grid color | 3, 4 |
| 7 — Build + deploy | 5, 6 |
