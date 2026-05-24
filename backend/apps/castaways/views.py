import json
from pathlib import Path

import requests as http_client
from django.conf import settings
from django.http import Http404, HttpResponse
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Season, Castaway, Episode
from .serializers import CastawaySerializer, EpisodeSerializer, SeasonSerializer
from .wiki_images import HEADERS as FANDOM_HEADERS


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


class CastawayImageProxyView(APIView):
    """
    GET /api/v1/castaways/<castaway_id>/image/

    Proxies the castaway's headshot from the Fandom CDN through our own server.
    Public (no auth) so browsers can load it via a plain <img> tag.
    Browser-side result is cached for 24 h via Cache-Control.
    """
    permission_classes = [AllowAny]
    throttle_classes = []  # image loads are not a security surface; exempt from rate limits

    def get(self, request, castaway_id):
        try:
            castaway = Castaway.objects.get(castaway_id=castaway_id)
        except Castaway.DoesNotExist:
            raise Http404

        if not castaway.image_url:
            raise Http404

        try:
            resp = http_client.get(castaway.image_url, headers=FANDOM_HEADERS, timeout=10)
        except Exception:
            raise Http404

        if resp.status_code != 200:
            raise Http404

        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        response = HttpResponse(resp.content, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=86400'
        return response


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
