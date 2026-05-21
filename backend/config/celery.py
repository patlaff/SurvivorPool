import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('survivorpool')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'sync-season-data-daily': {
        'task': 'apps.scoring.tasks.sync_season_data',
        'schedule': crontab(hour=20, minute=0),  # 20:00 PT daily
    },
    'score-active-season-daily': {
        'task': 'apps.scoring.tasks.score_active_season',
        'schedule': crontab(hour=21, minute=5),  # 21:05 PT daily
    },
}
