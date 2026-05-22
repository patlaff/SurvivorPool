from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


class SurvivorPoolRefreshToken(RefreshToken):
    """
    Custom refresh token that embeds display fields and is_superadmin
    into the payload. SimpleJWT copies all non-reserved claims from the
    refresh token into the access token automatically, so these show up
    in str(token.access_token) without any extra work.
    """

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        # Set on the refresh token payload — SimpleJWT copies these to the access token
        token['email'] = user.email
        token['display_name'] = user.display_name
        token['avatar_url'] = user.avatar_url
        superadmin_emails = getattr(settings, 'SUPERADMIN_EMAILS', [])
        token['is_superadmin'] = user.email in superadmin_emails
        return token
