from django.core.exceptions import ValidationError
from django.db import models


class Season(models.Model):
    season_number = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=10, default='US')
    is_active = models.BooleanField(default=False)
    draft_lock_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['season_number']

    def clean(self):
        if self.version != 'US':
            raise ValidationError('Only US seasons are supported.')

    def __str__(self):
        return f'S{self.season_number}: {self.name}'


class Castaway(models.Model):
    castaway_id = models.CharField(max_length=20, unique=True)
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='castaways')
    name = models.CharField(max_length=255)
    age = models.IntegerField(null=True, blank=True)
    hometown = models.CharField(max_length=255, blank=True)
    occupation = models.CharField(max_length=255, blank=True)
    is_eliminated = models.BooleanField(default=False)
    eliminated_episode = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} (S{self.season.season_number})'


class Episode(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='episodes')
    episode_number = models.IntegerField()
    air_date = models.DateField()
    scored_at = models.DateTimeField(null=True, blank=True)
    is_merge = models.BooleanField(
        default=False,
        help_text='True on the first episode where the merged tribe appears.',
    )
    is_finale = models.BooleanField(
        default=False,
        help_text='True if this episode is the season finale.',
    )

    class Meta:
        unique_together = ('season', 'episode_number')
        ordering = ['episode_number']

    def __str__(self):
        return f'S{self.season.season_number}E{self.episode_number}'
