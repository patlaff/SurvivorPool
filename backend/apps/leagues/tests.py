from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.castaways.models import Castaway, Episode, Season
from apps.scoring.models import PlayerEpisodeScore
from .models import League, Membership, Perk, Roster, RosterSlot


def make_user(n):
    return User.objects.create(google_id=f'g{n}', email=f'u{n}@ex.com', username=f'g{n}', display_name=f'User {n}')


class LeagueAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.season = Season.objects.create(season_number=99, name='Test', version='US', is_active=True,
                                             draft_lock_date=date.today() + timedelta(days=30))
        self.user = make_user(1)
        self.client.force_authenticate(user=self.user)

    def test_create_league(self):
        r = self.client.post('/api/v1/leagues/', {'name': 'My League'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(League.objects.filter(name='My League').exists())
        self.assertTrue(Membership.objects.filter(league__name='My League', user=self.user).exists())

    def test_join_league(self):
        other = make_user(2)
        league = League.objects.create(name='Other', season=self.season, owner=other)
        Membership.objects.create(league=league, user=other)
        url = f'/api/v1/leagues/{league.slug}/join/'
        r = self.client.post(url, {'invite_code': league.invite_code}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_duplicate_join_rejected(self):
        league = League.objects.create(name='ML', season=self.season, owner=self.user)
        Membership.objects.create(league=league, user=self.user)
        url = f'/api/v1/leagues/{league.slug}/join/'
        r = self.client.post(url, {'invite_code': league.invite_code}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_non_member_cannot_read(self):
        other = make_user(3)
        league = League.objects.create(name='Private', season=self.season, owner=other)
        Membership.objects.create(league=league, user=other)
        url = f'/api/v1/leagues/{league.slug}/'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)


class DraftAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.season = Season.objects.create(season_number=98, name='Draft Test', version='US', is_active=True,
                                             draft_lock_date=date.today() + timedelta(days=30))
        self.user = make_user(10)
        self.client.force_authenticate(user=self.user)
        self.league = League.objects.create(name='DL', season=self.season, owner=self.user)
        Membership.objects.create(league=self.league, user=self.user)
        self.castaways = [
            Castaway.objects.create(castaway_id=f'US98{i:02d}', season=self.season, name=f'C{i}')
            for i in range(1, 8)
        ]

    def _draft_url(self):
        return f'/api/v1/leagues/{self.league.slug}/draft/'

    def test_draft_5_castaways(self):
        ids = [c.castaway_id for c in self.castaways[:5]]
        r = self.client.put(self._draft_url(), {'castaway_ids': ids}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RosterSlot.objects.count(), 5)

    def test_draft_revision_allowed(self):
        ids = [c.castaway_id for c in self.castaways[:5]]
        self.client.put(self._draft_url(), {'castaway_ids': ids}, format='json')
        new_ids = [c.castaway_id for c in self.castaways[2:7]]
        r = self.client.put(self._draft_url(), {'castaway_ids': new_ids}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RosterSlot.objects.count(), 5)

    def test_draft_after_lock_rejected(self):
        self.season.draft_lock_date = date.today() - timedelta(days=1)
        self.season.save()
        ids = [c.castaway_id for c in self.castaways[:5]]
        r = self.client.put(self._draft_url(), {'castaway_ids': ids}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_fewer_than_5_rejected(self):
        ids = [c.castaway_id for c in self.castaways[:3]]
        r = self.client.put(self._draft_url(), {'castaway_ids': ids}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_duplicate_in_submission_rejected(self):
        ids = [self.castaways[0].castaway_id] * 5
        r = self.client.put(self._draft_url(), {'castaway_ids': ids}, format='json')
        self.assertEqual(r.status_code, 400)


class PerkAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.season = Season.objects.create(season_number=97, name='Perk Test', version='US', is_active=True,
                                             draft_lock_date=date.today() - timedelta(days=1))
        self.user = make_user(20)
        self.client.force_authenticate(user=self.user)
        self.league = League.objects.create(name='PL', season=self.season, owner=self.user)
        Membership.objects.create(league=self.league, user=self.user)
        self.episode = Episode.objects.create(season=self.season, episode_number=3, air_date=date.today() + timedelta(days=7))
        self.castaways = [
            Castaway.objects.create(castaway_id=f'US97{i:02d}', season=self.season, name=f'P{i}')
            for i in range(1, 8)
        ]
        self.roster = Roster.objects.create(league=self.league, user=self.user)
        for i, c in enumerate(self.castaways[:5], 1):
            RosterSlot.objects.create(roster=self.roster, castaway=c, slot_number=i)
        Perk.objects.create(roster=self.roster, perk_type=Perk.BOOST)
        Perk.objects.create(roster=self.roster, perk_type=Perk.SWAP)

    def test_boost_episode(self):
        url = f'/api/v1/leagues/{self.league.slug}/roster/boost/'
        r = self.client.post(url, {'episode_number': 3}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Perk.objects.get(roster=self.roster, perk_type=Perk.BOOST).used)

    def test_boost_used_twice_rejected(self):
        url = f'/api/v1/leagues/{self.league.slug}/roster/boost/'
        self.client.post(url, {'episode_number': 3}, format='json')
        r = self.client.post(url, {'episode_number': 3}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_boost_scored_episode_rejected(self):
        from django.utils import timezone as tz
        self.episode.scored_at = tz.now()
        self.episode.save()
        url = f'/api/v1/leagues/{self.league.slug}/roster/boost/'
        r = self.client.post(url, {'episode_number': 3}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_swap_castaway(self):
        url = f'/api/v1/leagues/{self.league.slug}/roster/swap/'
        r = self.client.post(url, {
            'out_id': self.castaways[0].castaway_id,
            'in_id': self.castaways[5].castaway_id,
        }, format='json')
        self.assertEqual(r.status_code, 200)

    def test_cross_user_roster_read(self):
        other = make_user(21)
        Membership.objects.create(league=self.league, user=other)
        other_roster = Roster.objects.create(league=self.league, user=other)
        url = f'/api/v1/leagues/{self.league.slug}/roster/{other.id}/'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_cross_user_swap_rejected(self):
        other = make_user(22)
        Membership.objects.create(league=self.league, user=other)
        other_roster = Roster.objects.create(league=self.league, user=other)
        for i, c in enumerate(self.castaways[:5], 1):
            RosterSlot.objects.get_or_create(roster=other_roster, castaway=c, defaults={'slot_number': i + 10})
        self.client.force_authenticate(user=other)
        url = f'/api/v1/leagues/{self.league.slug}/roster/swap/'
        r = self.client.post(url, {
            'out_id': self.castaways[0].castaway_id,
            'in_id': self.castaways[6].castaway_id,
        }, format='json')
        # Should fail — castaway already on another roster
        self.assertEqual(r.status_code, 400)
