# Design: Tribe Info on Castaways

## Backend

### 1 — Model change: `Castaway`

**File:** `backend/apps/castaways/models.py`

Add two new nullable fields:

```python
class Castaway(models.Model):
    ...
    original_tribe = models.CharField(max_length=100, blank=True)
    tribe_color = models.CharField(max_length=10, blank=True)  # hex, e.g. "#ff4148"
```

Both `blank=True` so existing records and any castaway without tribe data are handled gracefully.

---

### 2 — Sync task update

**File:** `backend/apps/scoring/tasks.py`

Inside `_sync_season`, after loading `castaways.json`, build a tribe-color lookup from `tribe_colours.json`:

```python
# Build original-tribe → hex color map for this season
tribe_color_map: dict[str, str] = {}
try:
    tc = _fetch_json('tribe_colours')
    us_tc = _filter_us_season(tc, season_number)
    original_tribes = us_tc[us_tc['tribe_status'] == 'Original']
    tribe_color_map = dict(
        zip(original_tribes['tribe'], original_tribes['tribe_colour'])
    )
except Exception:
    logger.debug('tribe_colours unavailable — tribe colors will be blank')
```

Then in the `update_or_create` call for each castaway, include:

```python
original_tribe_val = str(row.get('original_tribe') or '').strip()
defaults={
    ...
    'original_tribe': original_tribe_val,
    'tribe_color': tribe_color_map.get(original_tribe_val, ''),
}
```

---

### 3 — Serializer update

**File:** `backend/apps/castaways/serializers.py`

Add `original_tribe` and `tribe_color` to `CastawaySerializer.fields`:

```python
class CastawaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Castaway
        fields = (
            'castaway_id', 'name', 'age', 'hometown', 'occupation',
            'image_url', 'is_eliminated', 'eliminated_episode',
            'original_tribe', 'tribe_color',
        )
```

---

### 4 — Migration

Run `makemigrations` and `migrate` inside the container after model change.

---

## Frontend

### 5 — TypeScript type update

**File:** `frontend/src/api/leagues.ts`

Add to `Castaway` interface:

```typescript
export interface Castaway {
  ...
  original_tribe: string
  tribe_color: string
}
```

---

### 6 — Draft page: tribe badge on castaway cards

**File:** `frontend/src/pages/DraftPage.tsx`

Inside the castaway card, below the occupation line, add a tribe badge when `original_tribe` is set. Use an inline `backgroundColor` style since tribe colors are dynamic hex values and can't be expressed as Tailwind classes at build time:

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

---

### 7 — Picks grid: color-coded castaway names

**File:** `frontend/src/pages/LeaguePage.tsx`

In `PicksGridTab`, the castaway name cell currently renders:

```tsx
<span className={castaway.is_eliminated ? 'line-through text-gray-400' : 'text-gray-800'}>
  {castaway.name}
</span>
```

Update to apply the tribe color as `color` via inline style when `tribe_color` is set and the castaway is not eliminated (eliminated castaways keep the gray-out):

```tsx
<span
  className={castaway.is_eliminated ? 'line-through text-gray-400' : 'font-medium'}
  style={!castaway.is_eliminated && castaway.tribe_color ? { color: castaway.tribe_color } : undefined}
>
  {castaway.name}
</span>
```

Note: the picks grid data flows through `PicksGridResponse.castaways` which uses the same `Castaway` type — no separate API change needed.

---

## Files changed

| File | Change |
|------|--------|
| `backend/apps/castaways/models.py` | Add `original_tribe` + `tribe_color` fields |
| `backend/apps/scoring/tasks.py` | Fetch `tribe_colours.json`, populate fields during sync |
| `backend/apps/castaways/serializers.py` | Expose new fields in `CastawaySerializer` |
| `backend/apps/castaways/migrations/` | Generated migration |
| `frontend/src/api/leagues.ts` | Add fields to `Castaway` TypeScript interface |
| `frontend/src/pages/DraftPage.tsx` | Tribe badge on each castaway card |
| `frontend/src/pages/LeaguePage.tsx` | Color-code names in picks grid |
