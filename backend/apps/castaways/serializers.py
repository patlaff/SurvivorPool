from rest_framework import serializers
from .models import Season, Castaway, Episode


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ('season_number', 'name', 'is_active', 'draft_lock_date')


class CastawaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Castaway
        fields = ('castaway_id', 'name', 'age', 'hometown', 'occupation', 'image_url', 'is_eliminated', 'eliminated_episode')


class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ('episode_number', 'air_date', 'scored_at', 'is_merge', 'is_finale')
