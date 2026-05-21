from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import GoogleLoginView, MeView

urlpatterns = [
    path('auth/google/', GoogleLoginView.as_view(), name='auth-google'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
]
