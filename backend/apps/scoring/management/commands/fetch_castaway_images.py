import time

from django.core.management.base import BaseCommand

from apps.castaways.models import Castaway
from apps.castaways.wiki_images import fetch_fandom_image


class Command(BaseCommand):
    help = 'Backfill image_url for castaways that are missing one from survivor.fandom.com'

    def add_arguments(self, parser):
        parser.add_argument('--season', type=int, help='Limit to a specific season number')
        parser.add_argument('--force', action='store_true', help='Re-fetch even if image_url is already set')

    def handle(self, *args, **options):
        qs = Castaway.objects.all()
        if options['season']:
            qs = qs.filter(season__season_number=options['season'])
        if not options['force']:
            qs = qs.filter(image_url='')

        total = qs.count()
        self.stdout.write(f'Fetching images for {total} castaway(s)…')

        updated = 0
        for castaway in qs:
            img_url = fetch_fandom_image(castaway.name)
            if img_url:
                castaway.image_url = img_url
                castaway.save(update_fields=['image_url'])
                updated += 1
                self.stdout.write(f'  ✓ {castaway.name}')
            else:
                self.stdout.write(self.style.WARNING(f'  ✗ {castaway.name} (not found)'))
            time.sleep(0.5)  # polite crawl delay

        self.stdout.write(self.style.SUCCESS(f'Done — updated {updated}/{total} castaways.'))
