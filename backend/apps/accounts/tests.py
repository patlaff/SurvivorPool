from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import User


FAKE_PAYLOAD = {
    'sub': 'google-sub-123',
    'email': 'test@example.com',
    'name': 'Test User',
    'picture': 'https://example.com/photo.jpg',
}


class GoogleLoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('auth-google')

    @patch('apps.accounts.views.id_token.verify_oauth2_token')
    def test_valid_token_creates_user_and_returns_jwts(self, mock_verify):
        mock_verify.return_value = FAKE_PAYLOAD

        response = self.client.post(self.url, {'id_token': 'valid-token'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get()
        self.assertEqual(user.google_id, 'google-sub-123')
        self.assertEqual(user.email, 'test@example.com')
        self.assertFalse(user.has_usable_password())

    @patch('apps.accounts.views.id_token.verify_oauth2_token')
    def test_second_login_same_user_no_duplicate(self, mock_verify):
        mock_verify.return_value = FAKE_PAYLOAD
        self.client.post(self.url, {'id_token': 'token1'}, format='json')
        self.client.post(self.url, {'id_token': 'token2'}, format='json')

        self.assertEqual(User.objects.count(), 1)

    @patch('apps.accounts.views.id_token.verify_oauth2_token')
    def test_tampered_token_returns_400(self, mock_verify):
        mock_verify.side_effect = ValueError('Invalid token')

        response = self.client.post(self.url, {'id_token': 'bad-token'}, format='json')

        self.assertEqual(response.status_code, 400)

    def test_missing_token_returns_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)


class MeViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(
            google_id='g-me-123',
            email='me@example.com',
            username='g-me-123',
            display_name='Me User',
        )

    def test_authenticated_returns_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'me@example.com')

    def test_unauthenticated_returns_401(self):
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, 401)
