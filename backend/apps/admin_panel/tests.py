from unittest.mock import patch

import pandas as pd
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.castaways.models import Castaway, Episode, Season
from apps.scoring.tasks import _probe_next_season


@override_settings(SUPERADMIN_EMAILS=['admin@example.com'])
class RefreshSeasonDataViewTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', email='admin@example.com', display_name='Admin', google_id='g1')
        self.other = User.objects.create_user(
            username='other', email='nobody@example.com', display_name='Nobody', google_id='g2')
        self.season = Season.objects.create(season_number=49, name='S49', version='US', is_active=True)
        Castaway.objects.create(castaway_id='US0001', season=self.season, name='A')
        Episode.objects.create(season=self.season, episode_number=1, air_date='2026-02-25')
        self.url = reverse('admin-refresh-season-data')

    def test_requires_superadmin(self):
        self.client.force_authenticate(self.other)
        r = self.client.post(self.url)
        self.assertIn(r.status_code, (401, 403))

    def test_refresh_reports_no_next_data(self):
        self.client.force_authenticate(self.admin)
        with patch('apps.scoring.tasks._sync_season') as sync, \
             patch('apps.scoring.tasks._probe_next_season', return_value=0) as probe:
            r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200, r.content)
        sync.assert_called_once_with(49)
        probe.assert_called_once()
        self.assertTrue(probe.call_args.kwargs.get('force'))
        data = r.json()
        self.assertEqual(data['season_number'], 49)
        self.assertEqual(data['castaways'], 1)
        self.assertEqual(data['episodes'], 1)
        self.assertEqual(data['next_season_number'], 50)
        self.assertFalse(data['next_detected'])
        self.assertIn('No Season 50 data yet', data['detail'])

    def test_refresh_detects_next_season(self):
        self.client.force_authenticate(self.admin)

        def fake_probe(season, force=False):
            season.next_detected_at = timezone.now()
            season.save(update_fields=['next_detected_at'])
            return 18

        with patch('apps.scoring.tasks._sync_season'), \
             patch('apps.scoring.tasks._probe_next_season', side_effect=fake_probe):
            r = self.client.post(self.url)
        data = r.json()
        self.assertTrue(data['newly_detected'])
        self.assertTrue(data['next_detected'])
        self.assertEqual(data['next_season_castaways'], 18)
        self.assertIn('Season 50 data detected', data['detail'])

    def test_sync_failure_returns_500(self):
        self.client.force_authenticate(self.admin)
        with patch('apps.scoring.tasks._sync_season', side_effect=RuntimeError('boom')):
            r = self.client.post(self.url)
        self.assertEqual(r.status_code, 500)
        self.assertIn('boom', r.json()['detail'])

    def test_no_active_season(self):
        Season.objects.update(is_active=False)
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 400)


class ProbeNextSeasonForceTest(TestCase):
    def test_force_probes_even_when_notifications_already_sent(self):
        now = timezone.now()
        season = Season.objects.create(
            season_number=49, name='S49', version='US', is_active=True,
            next_detected_at=now, next_complete_notified_at=now,
        )
        rows = pd.DataFrame([{'version': 'US', 'season': 50, 'castaway_id': f'US{i}'} for i in range(20)])

        with patch('apps.scoring.tasks._fetch_json', return_value=rows) as fetch:
            self.assertEqual(_probe_next_season(season), 0)
            fetch.assert_not_called()
            self.assertEqual(_probe_next_season(season, force=True), 20)
            fetch.assert_called_once()
