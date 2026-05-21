from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
from django.test import TestCase

from apps.accounts.models import User
from apps.castaways.models import Castaway, Episode, Season
from apps.leagues.models import League, Perk, Roster, RosterSlot
from apps.scoring.event_detector import (
    detect_advance_a_week,
    detect_eliminated,
    detect_find_idol,
    detect_go_to_rocks,
    detect_individual_immunity,
    detect_sole_survivor,
    detect_survive_tribal,
)
from apps.scoring.models import PlayerEpisodeScore, ScoringEvent


def _tables(**overrides):
    base = {
        'advantage_movement': pd.DataFrame(),
        'advantage_details': pd.DataFrame(),
        'vote_history': pd.DataFrame(),
        'challenge_results': pd.DataFrame(),
        'castaways': pd.DataFrame(),
        'boot_mapping': pd.DataFrame(),
        'episodes': pd.DataFrame(),
        'jury_votes': pd.DataFrame(),
        'season_summary': pd.DataFrame(),
    }
    base.update(overrides)
    return base


class FindIdolDetectorTest(TestCase):
    def test_detects_found_idol(self):
        details = pd.DataFrame([
            {'advantage_id': 'a1', 'advantage_type': 'Hidden Immunity Idol', 'clue_details': None}
        ])
        movement = pd.DataFrame([
            {'advantage_id': 'a1', 'event': 'Found', 'castaway_id': 'US5001', 'episode': 3}
        ])
        results = detect_find_idol(_tables(advantage_movement=movement, advantage_details=details))
        self.assertEqual(results, [('US5001', 3, 'find_idol')])

    def test_ignores_played_event(self):
        details = pd.DataFrame([
            {'advantage_id': 'a1', 'advantage_type': 'Hidden Immunity Idol', 'clue_details': None}
        ])
        movement = pd.DataFrame([
            {'advantage_id': 'a1', 'event': 'Played', 'castaway_id': 'US5001', 'episode': 5}
        ])
        results = detect_find_idol(_tables(advantage_movement=movement, advantage_details=details))
        self.assertEqual(results, [])


class IndividualImmunityDetectorTest(TestCase):
    def test_detects_immunity_win(self):
        cr = pd.DataFrame([
            {'castaway_id': 'US5002', 'challenge_type': 'immunity', 'result': 'Win', 'episode': 4}
        ])
        results = detect_individual_immunity(_tables(challenge_results=cr))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][2], 'individual_immunity')


class SurviveTribalDetectorTest(TestCase):
    def test_detects_survivor(self):
        votes = pd.DataFrame([
            {'castaway_id': 'US5001', 'vote': 'US5003', 'episode': 2, 'voted_out': False},
            {'castaway_id': 'US5002', 'vote': 'US5003', 'episode': 2, 'voted_out': False},
            {'castaway_id': 'US5003', 'vote': 'US5001', 'episode': 2, 'voted_out': True},
        ])
        results = detect_survive_tribal(_tables(vote_history=votes))
        ids = [r[0] for r in results]
        self.assertIn('US5001', ids)
        self.assertIn('US5002', ids)
        self.assertNotIn('US5003', ids)


class EliminatedDetectorTest(TestCase):
    def test_detects_voted_out(self):
        castaways = pd.DataFrame([
            {'castaway_id': 'US5003', 'result': 'Voted Out', 'episode': 2}
        ])
        results = detect_eliminated(_tables(castaways=castaways))
        self.assertEqual(results, [('US5003', 2, 'eliminated')])


class GoToRocksDetectorTest(TestCase):
    def test_detects_rocks(self):
        votes = pd.DataFrame([
            {'castaway_id': 'US5001', 'vote': 'Black rock', 'episode': 6},
            {'castaway_id': 'US5002', 'vote': 'White rock', 'episode': 6},
        ])
        results = detect_go_to_rocks(_tables(vote_history=votes))
        self.assertEqual(len(results), 2)


class SoleSurvivorDetectorTest(TestCase):
    def test_detects_winner(self):
        castaways = pd.DataFrame([
            {'castaway_id': 'US5001', 'winner': True, 'finalist': True, 'episode': 13}
        ])
        results = detect_sole_survivor(_tables(castaways=castaways))
        self.assertEqual(results[0][2], 'sole_survivor')


class ScoringEngineTest(TestCase):
    def setUp(self):
        self.season = Season.objects.create(season_number=99, name='Test Season', version='US', is_active=True)
        self.episode = Episode.objects.create(season=self.season, episode_number=1, air_date=date(2025, 1, 1))
        self.castaway = Castaway.objects.create(castaway_id='US9901', season=self.season, name='Alice')
        self.user = User.objects.create(google_id='g-test', email='test@ex.com', username='g-test')
        self.league = League.objects.create(name='Test League', season=self.season, owner=self.user)
        self.roster = Roster.objects.create(league=self.league, user=self.user)
        RosterSlot.objects.create(roster=self.roster, castaway=self.castaway, slot_number=1)
        Perk.objects.create(roster=self.roster, perk_type=Perk.BOOST)
        Perk.objects.create(roster=self.roster, perk_type=Perk.SWAP)

    def _inject_event(self, event_name, points):
        ScoringEvent.objects.create(castaway=self.castaway, episode=self.episode, event_name=event_name, points=points)

    def test_player_episode_score_sums_correctly(self):
        self._inject_event('find_idol', 20)
        self._inject_event('survive_tribal', 15)

        from apps.scoring.engine import score_episode
        with patch('apps.scoring.engine.load_tables') as mock_load, \
             patch('apps.scoring.engine.check_episode_ready'), \
             patch('apps.scoring.engine.detect_all_events', return_value=[]):
            mock_load.return_value = {}
            score_episode(99, 1)

        score = PlayerEpisodeScore.objects.get(roster=self.roster, episode=self.episode)
        self.assertEqual(score.raw_points, 35)
        self.assertEqual(score.final_points, 35)

    def test_boost_perk_doubles_points(self):
        self._inject_event('individual_immunity', 25)
        boost = Perk.objects.get(roster=self.roster, perk_type=Perk.BOOST)
        boost.used = True
        boost.boost_target_episode = 1
        boost.save()

        from apps.scoring.engine import score_episode
        with patch('apps.scoring.engine.load_tables') as mock_load, \
             patch('apps.scoring.engine.check_episode_ready'), \
             patch('apps.scoring.engine.detect_all_events', return_value=[]):
            mock_load.return_value = {}
            score_episode(99, 1)

        score = PlayerEpisodeScore.objects.get(roster=self.roster, episode=self.episode)
        self.assertEqual(score.multiplier, Decimal('2.0'))
        self.assertEqual(score.final_points, 50)
