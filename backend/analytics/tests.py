from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch
from analytics.models import CustomUser, Game, Token, Queue, Client
import jwt
from django.conf import settings
from datetime import datetime, timedelta, timezone

class SignInAPIViewTests(APITestCase):
    def test_get_signin_page(self):
        url = reverse('signup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b'sign_in.html', response.content) 


class AuthReceiverAPIViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('auth-receiver')

    @patch('backend.views.id_token.verify_oauth2_token')
    def test_post_valid_token_existing_user(self, mock_verify):
        # Create user
        user = CustomUser.objects.create_user(email='test@example.com', username='testuser', password='pass123')
        mock_verify.return_value = {'email': 'test@example.com'}

        response = self.client.post(self.url, {'credential': 'fake-token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['email'], 'test@example.com')

    @patch('backend.views.id_token.verify_oauth2_token')
    def test_post_valid_token_creates_user(self, mock_verify):
        mock_verify.return_value = {'email': 'newuser@example.com'}
        response = self.client.post(self.url, {'credential': 'fake-token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CustomUser.objects.filter(email='newuser@example.com').exists())

    def test_post_missing_token(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('backend.views.id_token.verify_oauth2_token', side_effect=Exception("Invalid token"))
    def test_post_invalid_token(self, mock_verify):
        response = self.client.post(self.url, {'credential': 'bad-token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PasswordResetConfirmViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email='reset@example.com', password='oldpass')
        self.token_payload = {
            'user_id': self.user.id,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            'iat': datetime.now(timezone.utc)
        }
        self.token = jwt.encode(self.token_payload, settings.SECRET_KEY, algorithm='HS256')
        self.url = reverse('reset_password_confirm', args=[self.token]) 

    def test_post_successful_password_reset(self):
        data = {'password': 'newpassword123', 'confirm_password': 'newpassword123'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))

    def test_post_passwords_do_not_match(self):
        data = {'password': 'newpass', 'confirm_password': 'otherpass'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_missing_password_fields(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_expired_token(self):
        expired_token = jwt.encode(
            {
                'user_id': self.user.id,
                'exp': datetime.now(timezone.utc) - timedelta(hours=1),
                'iat': datetime.now(timezone.utc) - timedelta(hours=2)
            },
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        url = reverse('password-reset-confirm', args=[expired_token])
        response = self.client.post(url, {'password': 'pass', 'confirm_password': 'pass'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email='request@example.com', password='pass123')
        self.url = reverse('request_reset_password')

    @patch('backend.views.send_mail')
    def test_post_send_reset_link(self, mock_send_mail):
        response = self.client.post(self.url, {'email': self.user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()
        self.assertIn('message', response.data)

    def test_post_user_not_found(self):
        response = self.client.post(self.url, {'email': 'nonexistent@example.com'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CustomUserSignUpViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('signup')  # Replace with your url name

    def test_post_valid_signup(self):
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'pass123',
            'confirm_password': 'pass123'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CustomUser.objects.filter(email='newuser@example.com').exists())

    def test_post_invalid_signup(self):
        data = {
            'username': '',
            'email': 'invalid-email',
            'password': 'pass123',
            'confirm_password': 'differentpass'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='loginuser', email='login@example.com', password='pass123')
        self.url = reverse('login')

    def test_post_valid_login(self):
        data = {'email': self.user.email, 'password': 'pass123'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_post_invalid_login(self):
        data = {'email': self.user.email, 'password': 'wrongpass'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GameViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='gameuser', email='gameuser@example.com', password='pass123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('game')

    def test_get_games_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['games'], [])

    def test_post_create_game(self):
        data = {'name': 'Test Game', 'platform': ['PC'], 'thumbnail': None}  # Adjust fields as per your serializer
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')

    def test_post_invalid_game(self):
        data = {'name': '', 'platform': []}  # Invalid data
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='tokenuser', email='token@example.com', password='pass123')
        self.token = Token.objects.create(value='testtoken', Product=Game.objects.create(name='Game1', owner=self.user))
        self.url = reverse('tooken') 

    def test_get_token_missing_auth_header(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)  # Your view throws generic error if missing token

    def test_get_token_valid(self):
        self.client.credentials(HTTP_AUTHORIZATION='testtoken')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rb_username', response.data)

    def test_post_token_create(self):
        data = {
            'username': self.user.username,
            'name': 'testtokenname',
            'queues': []
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
