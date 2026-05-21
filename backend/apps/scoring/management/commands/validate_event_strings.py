from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Print value_counts for advantage_movement.event and advantage_details.advantage_type for a season'

    def add_arguments(self, parser):
        parser.add_argument('season_number', type=int)

    def handle(self, *args, **options):
        from apps.scoring.data_loader import load_tables

        season = options['season_number']
        self.stdout.write(f'Loading data for US season {season}...\n')
        tables = load_tables(season, refresh=True)

        move = tables.get('advantage_movement')
        if move is not None and not move.empty and 'event' in move.columns:
            self.stdout.write('=== advantage_movement.event ===')
            self.stdout.write(str(move['event'].value_counts()))
            self.stdout.write('')

        details = tables.get('advantage_details')
        if details is not None and not details.empty and 'advantage_type' in details.columns:
            self.stdout.write('=== advantage_details.advantage_type ===')
            self.stdout.write(str(details['advantage_type'].value_counts()))
            self.stdout.write('')

        vote = tables.get('vote_history')
        if vote is not None and not vote.empty and 'vote' in vote.columns:
            self.stdout.write('=== vote_history.vote (sample) ===')
            self.stdout.write(str(vote['vote'].value_counts().head(20)))
