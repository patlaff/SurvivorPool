import secrets
import string
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from apps.castaways.models import Season, Castaway


def _invite_code():
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


def _unique_slug(name):
    base = slugify(name)
    slug = base
    n = 1
    while League.objects.filter(slug=slug).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


class League(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name='leagues')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='owned_leagues')
    invite_code = models.CharField(max_length=8, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Per-league draft window overrides (both null = use season.draft_lock_date default)
    draft_close_at = models.DateTimeField(
        null=True, blank=True,
        help_text='If set, the draft closes at this datetime (overrides season lock date).',
    )
    draft_force_open = models.BooleanField(
        default=False,
        help_text='When True, the draft is open regardless of draft_close_at or season lock date.',
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(self.name)
        if not self.invite_code:
            self.invite_code = _invite_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('league', 'user')

    def __str__(self):
        return f'{self.user} in {self.league}'


class Roster(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='rosters')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rosters')

    class Meta:
        unique_together = ('league', 'user')

    def __str__(self):
        return f'{self.user}\'s roster in {self.league}'


class RosterSlot(models.Model):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name='slots')
    castaway = models.ForeignKey(Castaway, on_delete=models.PROTECT, related_name='roster_slots')
    slot_number = models.IntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('roster', 'slot_number')
        constraints = [
            models.UniqueConstraint(
                fields=['roster', 'castaway'],
                name='unique_castaway_per_roster',
            ),
        ]

    def __str__(self):
        return f'Slot {self.slot_number}: {self.castaway.name}'


class Perk(models.Model):
    SWAP = 'swap'
    BOOST = 'boost'
    PERK_CHOICES = [(SWAP, 'Swap'), (BOOST, 'Boost')]

    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name='perks')
    perk_type = models.CharField(max_length=10, choices=PERK_CHOICES)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    boost_target_episode = models.IntegerField(null=True, blank=True)
    swapped_out_castaway = models.ForeignKey(
        Castaway, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='swapped_out_perks',
    )
    swapped_in_castaway = models.ForeignKey(
        Castaway, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='swapped_in_perks',
    )

    class Meta:
        unique_together = ('roster', 'perk_type')

    def __str__(self):
        return f'{self.perk_type} perk for {self.roster}'
