import mock

from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from core.utils import LogMutingTestMixinBase


class ContactRequestMobileProfileMutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.contact_requests']


class ContactRequestMobileProfileTest(ContactRequestMobileProfileMutingMixin, APITestCase):
    def setUp(self):
        super(ContactRequestMobileProfileTest, self).setUp()
        self.data = {
            'credit_rating': '780',
            'annual_income_amount': 100000,
            'monthly_housing_expense': 5000,
            'monthly_nonhousing_expense': 4000,
            'down_payment_amount': 80000,
            'email': 'test@example.com',
            'phone': '(301) 845-5678',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        self.url = reverse('contact_requests:contact_request_mobile_profile')

    @mock.patch('vendors.tasks.SalesforcePush.push')
    def test_create_mobile_profile(self, mock_saleforce_push):
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key, value in self.data.iteritems():
            self.assertEqual(value, response.data.get(key))
        mock_saleforce_push.assert_called_once()

    @mock.patch('vendors.tasks.SalesforcePush.push')
    def test_get_mobile_profile_id(self, mock_saleforce_push):
        self.client.post(self.url, self.data, format='json')
        response = self.client.get(reverse('contact_requests:mobile_profile_active'), format='json')
        self.assertIsNotNone(response.data.get('id'))
        mock_saleforce_push.assert_called_once()

    @mock.patch('vendors.tasks.SalesforcePush.push')
    def test_update_mobile_profile(self, mock_saleforce_push):
        self.client.post(self.url, self.data, format='json')
        response = self.client.get(reverse('contact_requests:mobile_profile_active'), format='json')
        mobile_profile_id = response.data['id']
        url = reverse('contact_requests:contact_request_mobile_profile_detail', kwargs={'pk': mobile_profile_id})
        data = {'credit_rating': 500}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.data['credit_rating'], u'500')
        mock_saleforce_push.assert_called_once()
