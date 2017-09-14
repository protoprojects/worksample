from django.core.urlresolvers import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_jwt import utils

from accounts.factories import CustomerFactory, USER_PASSWORD


class EncompassAPITest(APITestCase):
    def setUp(self):
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.user = CustomerFactory()
        super(EncompassAPITest, self).setUp()

    @property
    def auth_data(self):
        return {
            'username': self.user.email,
            'password': USER_PASSWORD
        }

    def get_auth(self):
        url = reverse('encompass_authentication')
        response = self.csrf_client.post(url, self.auth_data)
        return "JWT {}".format(response.data['token'])

    def test_jwt_authentication_valid(self):
        """
        Ensure JWT login view using POST works.

        """
        url = reverse('encompass_authentication')
        response = self.csrf_client.post(url, self.auth_data)
        decoded_payload = utils.jwt_decode_handler(response.data['token'])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(decoded_payload['username'], self.user.email)

    def test_jwt_authentication_missing_fields(self):
        """
        Ensure JWT login view using JSON POST fails if missing fields.

        """
        url = reverse('encompass_authentication')
        response = self.csrf_client.post(url, {'username': self.user.email}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_jwt_authentication_bad_creds(self):
        """
        Ensure JWT login view using JSON POST fails if bad credentials are used.

        """
        url = reverse('encompass_authentication')
        response = self.csrf_client.post(url, {'username': self.user.email, 'password': 'wrong'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_creation(self):
        url = reverse('encompass_users:user')
        data = {
            "email": "john.doe@example.com",
            "phone": "+380631938145"
        }
        response = self.csrf_client.post(url, data, format='json', HTTP_AUTHORIZATION=self.get_auth())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_creation_without_token(self):
        url = reverse('encompass_users:user')
        data = {
            "email": "john.doe@example.com",
            "phone": "+380631938145"
        }
        response = self.csrf_client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
