from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsLeagueMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        from apps.leagues.models import Membership
        league = obj if hasattr(obj, 'memberships') else getattr(obj, 'league', None)
        if league is None:
            return False
        return Membership.objects.filter(league=league, user=request.user).exists()


class IsLeagueOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        league = obj if hasattr(obj, 'owner') else getattr(obj, 'league', None)
        if league is None:
            return False
        return league.owner == request.user


class IsLeagueMemberOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        from apps.leagues.models import Membership
        league = obj if hasattr(obj, 'memberships') else getattr(obj, 'league', None)
        if league is None:
            return False
        if request.method in SAFE_METHODS:
            return Membership.objects.filter(league=league, user=request.user).exists()
        return league.owner == request.user
