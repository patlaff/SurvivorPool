from django.urls import path
from .views import (
    AdminArchiveSeasonView,
    AdminCastawayAliasView,
    AdminCastawaysView,
    AdminLeaguesView,
    AdminProgressSeasonView,
    AdminScoringConfigView,
    AdminScoringRescore,
    AdminScoringSummaryView,
    AdminScoreUnscoredView,
    AdminUnarchiveSeasonView,
)

urlpatterns = [
    path('admin/leagues/', AdminLeaguesView.as_view(), name='admin-leagues'),
    path('admin/scoring-config/', AdminScoringConfigView.as_view(), name='admin-scoring-config'),
    path('admin/rescore/<int:season_number>/', AdminScoringRescore.as_view(), name='admin-rescore'),
    path('admin/score-unscored/<int:season_number>/', AdminScoreUnscoredView.as_view(), name='admin-score-unscored'),
    path('admin/seasons/<int:season_number>/scoring-summary/', AdminScoringSummaryView.as_view(), name='admin-scoring-summary'),
    path('admin/archive-season/<int:season_number>/', AdminArchiveSeasonView.as_view(), name='admin-archive-season'),
    path('admin/progress-season/', AdminProgressSeasonView.as_view(), name='admin-progress-season'),
    path('admin/unarchive-season/<int:season_number>/', AdminUnarchiveSeasonView.as_view(), name='admin-unarchive-season'),
    path('admin/castaways/<int:season_number>/', AdminCastawaysView.as_view(), name='admin-castaways'),
    path('admin/castaways/<str:castaway_id>/alias/', AdminCastawayAliasView.as_view(), name='admin-castaway-alias'),
]
