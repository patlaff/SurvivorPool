from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sync castaways and episodes for a US season from survivoR2py'

    def add_arguments(self, parser):
        parser.add_argument('season_number', type=int)

    def handle(self, *args, **options):
        from apps.scoring.tasks import _sync_season
        season_number = options['season_number']
        self.stdout.write(f'Syncing season {season_number}...')
        _sync_season(season_number)
        self.stdout.write(self.style.SUCCESS(f'Season {season_number} synced.'))
