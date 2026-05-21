from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Score a specific episode immediately (bypasses the scheduled task)'

    def add_arguments(self, parser):
        parser.add_argument('season', type=int)
        parser.add_argument('episode', type=int)
        parser.add_argument('--refresh', action='store_true', help='Force refresh data cache')

    def handle(self, *args, **options):
        from apps.scoring.engine import score_episode
        from apps.scoring.data_loader import DataNotReadyError

        season = options['season']
        episode = options['episode']
        self.stdout.write(f'Scoring S{season}E{episode}...')
        try:
            score_episode(season, episode)
            self.stdout.write(self.style.SUCCESS(f'Done.'))
        except DataNotReadyError as e:
            self.stderr.write(self.style.ERROR(str(e)))
