import urllib
import uuid

import mock

from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.encoding import force_text
from rest_framework import status

from accounts import factories as accounts_factories, models as accounts_models
from accounts.tests.helpers import JWTAuthAPITestCase
from loans import models as loans_models, factories as loans_factories


class TestAdvisorProfileView(JWTAuthAPITestCase):
    def setUp(self):
        self.url = reverse('advisor-portal:advisor_profile_view')

    def test_request_from_anonymous_user_returns_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_request_from_non_advisor_user_returns_forbidden(self):
        # pylint: disable=attribute-defined-outside-init
        self.user = accounts_factories.UserFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        response = self.client.get(self.url, HTTP_AUTHORIZATION=self.get_jwt_auth())
        self.assertEqual(response.status_code, 403)

    def test_successful_retrieve_profile_info(self):
        # pylint: disable=attribute-defined-outside-init
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        response = self.client.get(self.url, HTTP_AUTHORIZATION=self.get_jwt_auth())
        self.assertEqual(response.status_code, 200)


class TestAdvisorLoanProfileGuidId(JWTAuthAPITestCase):
    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

    def _get_loan_profile_guid_id(self, guid, with_auth=True):
        return self.client.get(
            reverse('advisor-portal:advisor_loan_profile_guid_id_view', args=[guid]),
            HTTP_AUTHORIZATION=(self.get_jwt_auth() if with_auth else '')
        )

    def test_success(self):
        loan_profile = loans_factories.LoanProfileV1Factory(advisor=self.user)
        guid = force_text(loan_profile.guid)
        response = self._get_loan_profile_guid_id(guid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['id'], loan_profile.id)

    def test_no_auth_401(self):
        loan_profile = loans_factories.LoanProfileV1Factory(advisor=self.user)
        guid = force_text(loan_profile.guid)
        response = self._get_loan_profile_guid_id(guid, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('id', response.data)

    def test_wrong_auth_404(self):
        user_1 = accounts_factories.AdvisorFactory()
        loan_profile = loans_factories.LoanProfileV1Factory(advisor=user_1)
        guid = force_text(loan_profile.guid)
        response = self._get_loan_profile_guid_id(guid, with_auth=True)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.content, 'GUID not found: {}'.format(guid))

    def test_unknown_guid_404(self):
        loans_factories.LoanProfileV1Factory(advisor=self.user)
        guid = force_text(uuid.uuid4())
        response = self._get_loan_profile_guid_id(guid, with_auth=True)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_a_guid_no_match(self):
        loans_factories.LoanProfileV1Factory(advisor=self.user)
        guid = 'this-is-not-a-guid'
        with self.assertRaises(NoReverseMatch):
            self._get_loan_profile_guid_id(guid, with_auth=True)
