from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from apps.accounts.tokens import SurvivorPoolRefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import User
from .serializers import GoogleAuthSerializer, UserSerializer


class GoogleAuthThrottle(AnonRateThrottle):
    rate = '10/min'


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [GoogleAuthThrottle]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['id_token']

        try:
            payload = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            return Response(
                {'detail': 'Invalid Google token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_id = payload['sub']
        email = payload.get('email', '')
        display_name = payload.get('name', '')
        avatar_url = payload.get('picture', '')

        user, _ = User.objects.get_or_create(
            google_id=google_id,
            defaults={
                'email': email,
                'username': google_id,
                'display_name': display_name,
                'avatar_url': avatar_url,
            },
        )
        user.set_unusable_password()

        # Update profile fields on each login
        changed = False
        if user.display_name != display_name:
            user.display_name = display_name
            changed = True
        if user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            changed = True
        if changed:
            user.save(update_fields=['display_name', 'avatar_url'])

        refresh = SurvivorPoolRefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
