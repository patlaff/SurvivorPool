from django.contrib import admin
from .models import ScoringEvent, PlayerEpisodeScore


@admin.register(ScoringEvent)
class ScoringEventAdmin(admin.ModelAdmin):
    list_display = ('castaway', 'episode', 'event_name', 'points')
    list_filter = ('episode__season', 'event_name')
    search_fields = ('castaway__name', 'event_name')
    readonly_fields = ('castaway', 'episode', 'event_name', 'points')


@admin.register(PlayerEpisodeScore)
class PlayerEpisodeScoreAdmin(admin.ModelAdmin):
    list_display = ('roster', 'episode', 'raw_points', 'multiplier', 'final_points')
    list_filter = ('episode__season',)
    readonly_fields = ('roster', 'episode', 'raw_points', 'multiplier', 'final_points')
