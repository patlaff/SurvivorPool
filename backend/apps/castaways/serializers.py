from rest_framework import serializers
from .models import Season, Castaway, Episode


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ('season_number', 'name', 'is_active', 'draft_lock_date',
                  'allows_new_leagues', 'next_detected_at')


class CastawaySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Castaway
        fields = (
            'castaway_id', 'name', 'alias', 'display_name',
            'age', 'hometown', 'occupation',
            'image_url', 'original_tribe', 'tribe_color',
            'is_eliminated', 'eliminated_episode',
        )

    def get_image_url(self, obj):
        if not obj.image_url:
            return ''
        return f'/api/v1/castaways/{obj.castaway_id}/image/'


class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ('episode_number', 'air_date', 'scored_at', 'is_merge', 'is_finale')
