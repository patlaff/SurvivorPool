from django.conf import settings
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Allow access only to users whose email is in settings.SUPERADMIN_EMAILS."""

    message = 'Superadmin access required.'

    def has_permission(self, request, view):
        return (
            request.user is not None
            and request.user.is_authenticated
            and request.user.email in getattr(settings, 'SUPERADMIN_EMAILS', [])
        )
