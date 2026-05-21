from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Season, Castaway, Episode
from .serializers import CastawaySerializer, EpisodeSerializer


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
