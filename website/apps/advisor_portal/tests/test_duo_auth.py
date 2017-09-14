import mock

from django.conf import settings
from django.test import TestCase, override_settings

from advisor_portal.utils.duo_auth import (
    duo_authenticate, duo_authenticated, duo_check_login,
    duo_perform_login, duo_get_signature,
)


@override_settings(
    DUO_INTEGRATION_KEY='ikey',
    DUO_SECRET='duo_secret',
    SECRET_KEY='django_secret'
)
class TestDuoAuthUtils(TestCase):
    def test_duo_authenticate(self):
        request = mock.MagicMock(
            session={}
        )
        duo_authenticate(request, 'test@user.mail')
        self.assertEqual(request.session['duo_authenticated'], 'test@user.mail')

    def test_duo_is_authenticated(self):
        request = mock.MagicMock(
            session={
                'duo_authenticated': 'test@user.mail'
            }
        )
        self.assertTrue(duo_authenticated(request, 'test@user.mail'))

    def test_duo_is_not_authenticated(self):
        request = mock.MagicMock(
            session={}
        )
        self.assertFalse(duo_authenticated(request, 'test@user.mail'))

    def test_duo_check_login_true(self):
        request = mock.MagicMock(
            session={
                'duo_authenticated': 'test@user.mail'
            }
        )
        self.assertTrue(duo_check_login(request, 'test@user.mail'))
        self.assertNotIn('duo_jwt_email', request.session)

    def test_duo_check_login_false(self):
        request = mock.MagicMock(
            session={}
        )
        self.assertFalse(duo_check_login(request, 'test@user.mail'))
        self.assertEqual(request.session['duo_jwt_email'], 'test@user.mail')

    @mock.patch('advisor_portal.utils.duo_auth.duo_web')
    def test_duo_get_signature(self, mocked_duo):
        mocked_duo.sign_request = mock.MagicMock(
            return_value='test_signature'
        )
        request = mock.MagicMock(
            session={
                'duo_jwt_email': 'test@user.mail'
            }
        )
        self.assertEqual(duo_get_signature(request), 'test_signature')
        self.assertEqual(mocked_duo.sign_request.call_count, 1)
        call_args = mocked_duo.sign_request.call_args[0]
        self.assertEqual(call_args[0], settings.DUO_INTEGRATION_KEY)
        self.assertEqual(call_args[1], settings.DUO_SECRET)
        self.assertEqual(call_args[2], settings.SECRET_KEY)
        self.assertEqual(call_args[3], 'test@user.mail')

    @mock.patch('advisor_portal.utils.duo_auth.duo_web')
    def test_duo_perform_login_success(self, mocked_duo):
        mocked_duo.verify_response = mock.MagicMock(
            return_value='Something not None'
        )
        request = mock.MagicMock(
            session={
                'duo_jwt_email': 'test@user.mail',
            },
            POST={
                'sig_response': 'test_signature',
                'next': '/next_url',
            }
        )
        logged_in, next_url = duo_perform_login(request)
        self.assertTrue(logged_in)
        self.assertEqual(next_url, '/next_url')
        self.assertEqual(mocked_duo.verify_response.call_count, 1)
        call_args = mocked_duo.verify_response.call_args[0]
        self.assertEqual(call_args[0], settings.DUO_INTEGRATION_KEY)
        self.assertEqual(call_args[1], settings.DUO_SECRET)
        self.assertEqual(call_args[2], settings.SECRET_KEY)
        self.assertEqual(call_args[3], 'test_signature')
        self.assertNotIn('duo_jwt_email', request.session)

    @mock.patch('advisor_portal.utils.duo_auth.duo_web')
    def test_duo_perform_login_fail(self, mocked_duo):
        mocked_duo.verify_response = mock.MagicMock(
            return_value=None
        )
        request = mock.MagicMock(
            session={
                'duo_jwt_email': 'test@user.mail',
            },
            POST={
                'sig_response': 'test_signature',
                'next': '/next_url',
            }
        )
        logged_in, next_url = duo_perform_login(request)
        self.assertFalse(logged_in)
        self.assertIsNone(next_url)
        self.assertEqual(mocked_duo.verify_response.call_count, 1)
        call_args = mocked_duo.verify_response.call_args[0]
        self.assertEqual(call_args[0], settings.DUO_INTEGRATION_KEY)
        self.assertEqual(call_args[1], settings.DUO_SECRET)
        self.assertEqual(call_args[2], settings.SECRET_KEY)
        self.assertEqual(call_args[3], 'test_signature')
        self.assertIn('duo_jwt_email', request.session)
