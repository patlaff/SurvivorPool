from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.castaways.serializers import CastawaySerializer, EpisodeSerializer
from apps.scoring.models import PlayerEpisodeScore, ScoringEvent
from .models import League, Membership, Perk, Roster, RosterSlot
from .utils import is_draft_open


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ('user', 'joined_at')


class LeagueSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    draft_lock_date = serializers.SerializerMethodField()
    draft_open = serializers.SerializerMethodField()
    season_number = serializers.IntegerField(source='season.season_number', read_only=True)

    class Meta:
        model = League
        fields = ('id', 'name', 'slug', 'season_id', 'season_number', 'owner', 'member_count',
                  'draft_lock_date', 'draft_open', 'draft_close_at', 'draft_force_open',
                  'created_at')
        read_only_fields = ('slug', 'created_at')

    def get_member_count(self, obj):
        return obj.memberships.count()

    def get_draft_lock_date(self, obj):
        # Return the effective close datetime: league override if set, else season default.
        return obj.draft_close_at if obj.draft_close_at is not None else obj.season.draft_lock_date

    def get_draft_open(self, obj):
        return is_draft_open(obj)


class LeagueDetailSerializer(LeagueSerializer):
    members = MembershipSerializer(source='memberships', many=True, read_only=True)
    invite_code = serializers.CharField(read_only=True)

    class Meta(LeagueSerializer.Meta):
        fields = LeagueSerializer.Meta.fields + ('members', 'invite_code')


class PerkSerializer(serializers.ModelSerializer):
    swapped_out_castaway = CastawaySerializer(read_only=True)
    swapped_in_castaway = CastawaySerializer(read_only=True)

    class Meta:
        model = Perk
        fields = ('perk_type', 'used', 'used_at', 'boost_target_episode',
                  'swapped_out_castaway', 'swapped_in_castaway')


class ScoringEventSerializer(serializers.ModelSerializer):
    castaway_name = serializers.CharField(source='castaway.name', read_only=True)

    class Meta:
        model = ScoringEvent
        fields = ('castaway_name', 'event_name', 'points')


class RosterSlotSerializer(serializers.ModelSerializer):
    castaway = CastawaySerializer(read_only=True)
    events = serializers.SerializerMethodField()

    class Meta:
        model = RosterSlot
        fields = ('slot_number', 'castaway', 'added_at', 'events')

    def get_events(self, obj):
        episode = self.context.get('episode')
        qs = ScoringEvent.objects.filter(castaway=obj.castaway)
        if episode:
            qs = qs.filter(episode=episode)
        return ScoringEventSerializer(qs, many=True).data


class RosterSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    slots = RosterSlotSerializer(many=True, read_only=True)
    perks = PerkSerializer(many=True, read_only=True)
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = Roster
        fields = ('id', 'user', 'slots', 'perks', 'total_points')

    def get_total_points(self, obj):
        return sum(obj.episode_scores.values_list('final_points', flat=True))


class EpisodeScoreSerializer(serializers.ModelSerializer):
    episode_number = serializers.IntegerField(source='episode.episode_number')
    air_date = serializers.DateField(source='episode.air_date')

    class Meta:
        model = PlayerEpisodeScore
        fields = ('episode_number', 'air_date', 'raw_points', 'multiplier', 'final_points')


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user = UserSerializer()
    total_points = serializers.IntegerField()
    episodes = EpisodeScoreSerializer(many=True)
