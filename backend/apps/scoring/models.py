from django.db import models
from apps.castaways.models import Castaway, Episode
from apps.leagues.models import Roster


class ScoringEvent(models.Model):
    castaway = models.ForeignKey(Castaway, on_delete=models.CASCADE, related_name='scoring_events')
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='scoring_events')
    event_name = models.CharField(max_length=50)
    points = models.IntegerField()

    class Meta:
        unique_together = ('castaway', 'episode', 'event_name')
        ordering = ['episode__episode_number', 'castaway__name']

    def __str__(self):
        return f'{self.castaway.name} — {self.event_name} (+{self.points})'


class PlayerEpisodeScore(models.Model):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name='episode_scores')
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='player_scores')
    raw_points = models.IntegerField(default=0)
    multiplier = models.DecimalField(max_digits=3, decimal_places=1, default='1.0')
    final_points = models.IntegerField(default=0)

    class Meta:
        unique_together = ('roster', 'episode')
        ordering = ['-final_points']

    def __str__(self):
        return f'{self.roster} — E{self.episode.episode_number}: {self.final_points}pts'
