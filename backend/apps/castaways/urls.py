from django.urls import path
from .views import SeasonCastawaysView, SeasonEpisodesView

urlpatterns = [
    path('seasons/<int:season_number>/castaways/', SeasonCastawaysView.as_view(), name='season-castaways'),
    path('seasons/<int:season_number>/episodes/', SeasonEpisodesView.as_view(), name='season-episodes'),
]
