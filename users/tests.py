import logging

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()

VALID_USER = {
    'username': 'anna',
    'first_name': 'Анна',
    'last_name': 'Коваль',
    'email': 'anna@example.com',
    'password': 'Str0ng-pass-2026',
    'password_confirmation': 'Str0ng-pass-2026',
}


def bearer(token):
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


class LoggingTests(APITestCase):

    def setUp(self):
        logging.disable(logging.NOTSET)
        self.addCleanup(logging.disable, logging.CRITICAL)
        User.objects.create_user('anna', 'anna@example.com', 'Str0ng-pass-2026')

    def test_failed_login_is_warning_without_password(self):
        with self.assertLogs('users', level='WARNING') as logs:
            self.client.post(
                '/api/auth/login',
                {'username': 'anna', 'password': 'Wrong-pass-123'},
                format='json',
            )
        text = '\n'.join(logs.output)
        self.assertIn('WARNING', text)
        self.assertIn('anna', text)
        self.assertNotIn('Wrong-pass-123', text)

    def test_successful_login_is_info_without_tokens(self):
        with self.assertLogs('users', level='INFO') as logs:
            response = self.client.post(
                '/api/auth/login',
                {'username': 'anna', 'password': 'Str0ng-pass-2026'},
                format='json',
            )
        text = '\n'.join(logs.output)
        self.assertIn('INFO', text)
        self.assertNotIn('Str0ng-pass-2026', text)
        self.assertNotIn(response.data['access'], text)
        self.assertNotIn(response.data['refresh'], text)

    def test_registration_log_has_no_password(self):
        data = dict(VALID_USER, username='olena', email='olena@example.com')
        with self.assertLogs('users', level='INFO') as logs:
            self.client.post('/api/auth/register', data, format='json')
        text = '\n'.join(logs.output)
        self.assertIn('Зареєстровано', text)
        self.assertNotIn(data['password'], text)

    def test_bad_token_is_logged_without_the_token(self):
        with self.assertLogs('users', level='WARNING') as logs:
            self.client.get('/api/users/me', **bearer('garbage.token.value'))
        text = '\n'.join(logs.output)
        self.assertIn('токен відхилено', text)
        self.assertNotIn('garbage.token.value', text)