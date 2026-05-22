import json
from pathlib import Path

from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Season, Castaway, Episode
from .serializers import CastawaySerializer, EpisodeSerializer, SeasonSerializer


class SeasonCastawaysView(generics.ListAPIView):
    serializer_class = CastawaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Castaway.objects.filter(
            season__season_number=self.kwargs['season_number'],
            season__version='US',
        ).select_related('season')


class SeasonEpisodesView(generics.ListAPIView):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Episode.objects.filter(
            season__season_number=self.kwargs['season_number'],
            season__version='US',
        ).order_by('episode_number')


class ActiveSeasonView(APIView):
    """GET /api/v1/active-season/ — returns the active US season with its episodes."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        season = Season.objects.filter(is_active=True, version='US').first()
        if season is None:
            return Response({'detail': 'No active season found.'}, status=404)

        episodes = Episode.objects.filter(season=season).order_by('episode_number')
        return Response({
            'season': SeasonSerializer(season).data,
            'episodes': EpisodeSerializer(episodes, many=True).data,
        })


class PublicScoringConfigView(APIView):
    """GET /api/v1/scoring-config/ — read-only scoring config for all authenticated users."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        path = Path(getattr(settings, 'SCORING_CONFIG_PATH', settings.BASE_DIR / 'scoring_config.json'))
        try:
            with open(path) as f:
                config = json.load(f)
        except FileNotFoundError:
            return Response({'detail': 'Scoring config not found.'}, status=500)
        return Response({'config': config})
