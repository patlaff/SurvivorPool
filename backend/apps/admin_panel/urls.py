from django.urls import path
from .views import (
    AdminLeaguesView,
    AdminScoringConfigView,
    AdminScoringRescore,
    AdminScoringSummaryView,
    AdminScoreUnscoredView,
)

urlpatterns = [
    path('admin/leagues/', AdminLeaguesView.as_view(), name='admin-leagues'),
    path('admin/scoring-config/', AdminScoringConfigView.as_view(), name='admin-scoring-config'),
    path('admin/rescore/<int:season_number>/', AdminScoringRescore.as_view(), name='admin-rescore'),
    path('admin/score-unscored/<int:season_number>/', AdminScoreUnscoredView.as_view(), name='admin-score-unscored'),
    path('admin/seasons/<int:season_number>/scoring-summary/', AdminScoringSummaryView.as_view(), name='admin-scoring-summary'),
]
