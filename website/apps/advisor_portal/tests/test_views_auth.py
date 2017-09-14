import json

import mock

from django.core.urlresolvers import reverse
from django.test import override_settings

from rest_framework.test import APITestCase

from accounts import factories
from advisor_portal.tests.helpers import get_client_with_session
from core.serializers import jwt_encode_handler, jwt_payload_handler
from core.utils import FullDiffMixin


@override_settings(ADVISOR_PORTAL_DUO_AUTH_ENABLED=False)
class TestAdvisorPortalLoginView(FullDiffMixin, APITestCase):
    def setUp(self):
        self.url = reverse('advisor-portal:advisor_login')

    def test_missing_fields_returns_400(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 400)

        self.assertIn('username', response.data)
        self.assertIn('password', response.data)

    def test_wrong_credentials_returns_400(self):
        response = self.client.post(self.url, data={
            'username': 'test@test.com',
            'password': 'test',
        })

        self.assertEqual(response.status_code, 400)

        self.assertIn('non_field_errors', response.data)

    def test_wrong_user_type_can_not_login(self):
        factories.CustomerFactory(email='test@test.com')

        response = self.client.post(self.url, data={
            'username': 'test@test.com',
            'password': factories.USER_PASSWORD,
        })
        self.assertEqual(response.status_code, 400)

        self.assertIn('non_field_errors', response.data)

    def test_successful_login(self):
        user = factories.AdvisorFactory(email='test@test.com')

        response = self.client.post(self.url, data={
            'username': 'test@test.com',
            'password': factories.USER_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['token'],
            jwt_encode_handler(jwt_payload_handler(user))
        )


@override_settings(ADVISOR_PORTAL_DUO_AUTH_ENABLED=True)
class TestAdvisorPortalLoginViewWithDuo(APITestCase):
    def setUp(self):
        self.url = reverse('advisor-portal:advisor_login')
        self.client = get_client_with_session()

    def test_not_authenticated_with_duo(self):
        factories.AdvisorFactory(email='test@test.com')
        response = self.client.post(self.url, data={
            'username': 'test@test.com',
            'password': factories.USER_PASSWORD,
        })
        self.assertEqual(response.status_code, 401)

    def test_authenticated_with_duo(self):
        user = factories.AdvisorFactory(email='test@test.com')
        session = self.client.session
        session['duo_authenticated'] = user.email
        session.save()
        response = self.client.post(self.url, data={
            'username': 'test@test.com',
            'password': factories.USER_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)


class TestVerifyJSONWebTokenView(APITestCase):
    def setUp(self):
        self.url = reverse('advisor-portal:verify_token')

    def test_incorrect_token_returns_400(self):
        response = self.client.post(self.url, data={
            'token': 'blablatoken',
        })
        self.assertEqual(response.status_code, 400)

        self.assertIn('non_field_errors', response.data)

    def test_correct_token_returns_successful_response(self):
        user = factories.AdvisorFactory(email='test@test.com')
        response = self.client.post(self.url, data={
            'token': jwt_encode_handler(jwt_payload_handler(user)),
        })
        self.assertEqual(response.status_code, 204)


@override_settings(
    ADVISOR_PORTAL_DUO_AUTH_ENABLED=True,
    ADVISOR_PORTAL_DUO_API_HOST='test.host',
)
class TestAdvisorPortalDUOLoginView(FullDiffMixin, APITestCase):
    def setUp(self):
        self.url = reverse('advisor-portal:advisor_duo_login')
        self.client = get_client_with_session()

    @mock.patch('advisor_portal.views.auth.duo_get_signature')
    def test_successful_signature_retrieve(self, mocked_get_signature):
        mocked_get_signature.return_value = 'test_signature'
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content), 2)
        self.assertEqual(content['duo_signature'], 'test_signature')
        self.assertEqual(content['duo_host'], 'test.host')

    @mock.patch('advisor_portal.views.auth.duo_get_signature')
    def test_inability_to_get_signature_returns_403(self, mocked_get_signature):
        mocked_get_signature.return_value = None
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    @mock.patch('advisor_portal.views.auth.duo_perform_login')
    def test_successful_login(self, mocked_perform_login):
        mocked_perform_login.return_value = (True, '/next')
        response = self.client.post(self.url)
        self.assertRedirects(response, '/next', fetch_redirect_response=False)

    @mock.patch('advisor_portal.views.auth.duo_perform_login')
    def test_unsuccessful_login_returns_401(self, mocked_perform_login):
        mocked_perform_login.return_value = (False, None)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
