from django.urls import path
from .views import SeasonCastawaysView, SeasonEpisodesView, ActiveSeasonView, PublicScoringConfigView

urlpatterns = [
    path('seasons/<int:season_number>/castaways/', SeasonCastawaysView.as_view(), name='season-castaways'),
    path('seasons/<int:season_number>/episodes/', SeasonEpisodesView.as_view(), name='season-episodes'),
    path('active-season/', ActiveSeasonView.as_view(), name='active-season'),
    path('scoring-config/', PublicScoringConfigView.as_view(), name='public-scoring-config'),
]
