# Design: Perk Eligibility Controls

## Data Model

Add two boolean flags to `Episode`:

```python
# apps/castaways/models.py

class Episode(models.Model):
    # ... existing fields ...
    is_merge = models.BooleanField(
        default=False,
        help_text='True on the first episode where the merged tribe appears.',
    )
    is_finale = models.BooleanField(
        default=False,
        help_text='True if this episode is the season finale.',
    )
```

**Migration**: `apps/castaways/migrations/0002_episode_perk_flags.py`

---

## Flag Population (Data Sync)

Both flags are set inside `_sync_season` in `apps/scoring/tasks.py` after episodes are created/updated.

### `is_merge`

Derived from the `tribe_mapping` survivoR JSON table. The merge episode is the minimum `episode` number where `tribe_status == 'Merged'` for the season:

```python
tm = _fetch_json('tribe_mapping')
season_tm = _filter_us_season(tm, season_number)
merged = season_tm[season_tm['tribe_status'] == 'Merged']
if not merged.empty:
    merge_ep_num = int(merged['episode'].min())
    Episode.objects.filter(season=season_obj, episode_number=merge_ep_num).update(is_merge=True)
    # Clear stale flags on all other episodes
    Episode.objects.filter(season=season_obj).exclude(episode_number=merge_ep_num).update(is_merge=False)
```

### `is_finale`

Derived from the `episodes` survivoR JSON table. The finale episode has `episode_label == 'Finale'`:

```python
eps_df = _fetch_json('episodes')
season_eps = _filter_us_season(eps_df, season_number)
finale_rows = season_eps[season_eps['episode_label'] == 'Finale']
finale_ep_nums = finale_rows['episode'].tolist()
Episode.objects.filter(season=season_obj).update(is_finale=False)
Episode.objects.filter(season=season_obj, episode_number__in=finale_ep_nums).update(is_finale=True)
```

---

## Episode Serializer & Endpoint

### `EpisodeSerializer` update

Add `is_merge` and `is_finale` to `apps/castaways/serializers.py`:

```python
class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ('episode_number', 'air_date', 'scored_at', 'is_merge', 'is_finale')
```

### New endpoint: `GET /api/v1/seasons/<season_number>/episodes/`

```python
# apps/castaways/views.py
class SeasonEpisodesView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Episode.objects.filter(
            season__season_number=self.kwargs['season_number'],
            season__version='US',
        ).order_by('episode_number')
```

Registered in `apps/castaways/urls.py`:
```python
path('seasons/<int:season_number>/episodes/', SeasonEpisodesView.as_view(), name='season-episodes'),
```

---

## Backend Perk Validation

### `SwapPerkView.post` (updated logic)

Replace the current `lock_date` check with `is_draft_open()` and add the merge gate:

```python
# Draft must be closed before swapping
if is_draft_open(league):
    return Response(
        {'detail': 'Swaps are only available after the draft closes.'},
        status=status.HTTP_400_BAD_REQUEST,
    )

# Swap window closes when the merge episode airs
merge_ep = Episode.objects.filter(
    season=league.season, is_merge=True
).order_by('episode_number').first()
if merge_ep and merge_ep.air_date <= timezone.now().date():
    return Response(
        {'detail': 'Swap perk has expired — the tribes have merged.'},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

If no `is_merge` episode exists yet (merge hasn't been synced), swaps are allowed — the check only gates when a merge date is known.

### `BoostPerkView.post` (updated logic)

Add finale gate after the existing "already scored" check:

```python
episode = get_object_or_404(Episode, season=league.season, episode_number=episode_number)
if episode.scored_at is not None:
    return Response({'detail': 'That episode has already been scored.'}, status=400)
if episode.is_finale:
    return Response(
        {'detail': 'Boost cannot be applied to the finale.'},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

---

## API Response Shape

`GET /api/v1/seasons/50/episodes/` returns:

```json
[
  { "episode_number": 1,  "air_date": "2026-02-25", "scored_at": "...", "is_merge": false, "is_finale": false },
  { "episode_number": 7,  "air_date": "2026-04-08", "scored_at": null,  "is_merge": true,  "is_finale": false },
  { "episode_number": 13, "air_date": "2026-05-21", "scored_at": null,  "is_merge": false, "is_finale": true  }
]
```

---

## Frontend

### API layer (`frontend/src/api/leagues.ts`)

Add interface and hook:

```typescript
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
```

### `RosterPage.tsx` changes

Add `useLeague` and `useSeasonEpisodes` calls. Derive eligibility state:

```tsx
const { data: league } = useLeague(slug!)
const { data: episodes } = useSeasonEpisodes(league?.season_number ?? 0)

// Swap: window is open if no merge episode has aired yet
const mergeEpisode = episodes?.find(e => e.is_merge)
const swapWindowOpen = !mergeEpisode || new Date(mergeEpisode.air_date) > new Date()

// Boost: eligible episodes are future (unscored) and not the finale
const boostEligible = episodes?.filter(e => !e.scored_at && !e.is_finale) ?? []
```

**Swap perk card** — when `swap?.used` is false:
- If `swapWindowOpen`: show the existing swap form (no change)
- If `!swapWindowOpen`: replace button with a muted "Window closed — tribes merged Ep N" note

**Boost perk card** — replace the free-text episode number input with a `<select>` populated from `boostEligible`. If `boostEligible` is empty, show "No eligible episodes remaining."

---

## Eligibility Summary

| Perk  | Allowed when                                      | Blocked when                              |
|-------|---------------------------------------------------|-------------------------------------------|
| Swap  | Draft is closed AND merge has not yet aired       | Draft still open OR merge episode aired   |
| Boost | Target episode is unscored AND not the finale     | Episode already scored OR `is_finale=True`|
