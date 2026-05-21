from django.contrib import admin
from .models import Season, Castaway, Episode


class EpisodeInline(admin.TabularInline):
    model = Episode
    extra = 0
    readonly_fields = ('scored_at',)


class CastawayInline(admin.TabularInline):
    model = Castaway
    extra = 0


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('season_number', 'name', 'version', 'is_active', 'draft_lock_date')
    list_editable = ('is_active',)
    inlines = [EpisodeInline, CastawayInline]
    actions = ['force_sync']

    @admin.action(description='Force sync season data from survivoR2py')
    def force_sync(self, request, queryset):
        from apps.scoring.tasks import sync_season_data
        sync_season_data.delay()
        self.message_user(request, 'Sync task queued.')


@admin.register(Castaway)
class CastawayAdmin(admin.ModelAdmin):
    list_display = ('name', 'season', 'is_eliminated', 'eliminated_episode')
    list_filter = ('season', 'is_eliminated')
    search_fields = ('name', 'castaway_id')


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'air_date', 'scored_at')
    list_filter = ('season',)
    readonly_fields = ('scored_at',)
    actions = ['rescore']

    @admin.action(description='Re-score selected episodes')
    def rescore(self, request, queryset):
        from apps.scoring.engine import score_episode
        for ep in queryset:
            score_episode(ep.season.season_number, ep.episode_number)
        self.message_user(request, f'Rescored {queryset.count()} episode(s).')
