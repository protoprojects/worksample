import logging

from django.core.urlresolvers import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from core.utils import LogMutingTestMixinBase
from loans import models as loan_models
from mortgage_profiles.models import MortgageProfile, MortgageProfilePurchase, MortgageProfileRefinance

logger = logging.getLogger('sample.mortech.test')


class MortgageProfileMutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.mortgage_profiles']


class MortgageProfileCreateTest(MortgageProfileMutingMixin, APITestCase):
    def test_create_mortgage_profile_purchase_valid(self):
        """Ensure we can create a new mortgage profile purchase object."""
        url = reverse('mortgage_profiles:purchase_list')
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'first_time_homebuyer',
            'property_type': 'single_family'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('id'))

        created_obj = MortgageProfilePurchase.objects.get(uuid=response.data['id'])
        for key, value in data.iteritems():
            self.assertEqual(value, getattr(created_obj, key))
        self.assertEqual(created_obj.uuid, self.client.session['mortgage_profile_uuid'])

    def test_create_mortgage_profile_string_url_valid(self):
        """Ensure mortgage profile creates when url is string"""
        url = reverse('mortgage_profiles:purchase_list')
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'first_time_homebuyer',
            'property_type': 'single_family',
            'referral_url': 'string'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_mortgage_profile_readable_error_on_purchase_price_max_value_invalid(self):
        """Ensure mortgage profile gives correct error message when purchase price too high"""
        url = reverse('mortgage_profiles:purchase_list')
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'first_time_homebuyer',
            'property_type': 'single_family',
            'target_value': 250000000
        }
        response = self.client.post(url, data, format='json')
        expected = {'target_value': ['Purchase price must be less than $10,000,000.']}
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, expected)

    def test_create_mortgage_profile_5001_length_url_valid(self):
        """Ensure mortgage profile creates successfully when url is 1999 characters"""
        url = reverse('mortgage_profiles:purchase_list')
        referral_url = 'http://example.com/?q=' + ("x" * 4979)
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'first_time_homebuyer',
            'property_type': 'single_family',
            'referral_url': referral_url
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_mortgage_profile_refinance_valid(self):
        """Ensure we can create a new mortgage profile refinance object."""
        url = reverse('mortgage_profiles:refinance_list')
        data = {
            'kind': MortgageProfile.REFINANCE,
            'purpose': 'lower_mortgage_payments',
            'property_type': 'single_family',
            'property_value': 1000000,
            'mortgage_owe': 400000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('id'))

        created_obj = MortgageProfileRefinance.objects.get(uuid=response.data['id'])
        for key, value in data.iteritems():
            self.assertEqual(value, getattr(created_obj, key))
        self.assertEqual(created_obj.uuid, self.client.session['mortgage_profile_uuid'])


class MortgageProfileDetailTest(MortgageProfileMutingMixin, APITestCase):
    maxDiff = None

    def _create_mp(self, purchase=True):
        reverse_arg = 'mortgage_profiles:purchase_list' if purchase else 'mortgage_profiles:refinance_list'
        url = reverse(reverse_arg)

        kind = MortgageProfile.PURCHASE if purchase else MortgageProfile.REFINANCE
        data = {'kind': kind}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('id'))
        cls = MortgageProfilePurchase if purchase else MortgageProfileRefinance
        return cls.objects.get(uuid=response.data['id'])

    def _update_mp(self, mp, data, purchase=True):
        reverse_arg = 'mortgage_profiles:purchase_details' if purchase else 'mortgage_profiles:refinance_details'
        url = reverse(reverse_arg, args=[mp.uuid])
        return self.client.put(url, data=data)

    def _get_mp(self, mp, purchase=True):
        reverse_arg = 'mortgage_profiles:purchase_details' if purchase else 'mortgage_profiles:refinance_details'
        url = reverse(reverse_arg, args=[mp.uuid])
        response = self.client.get(url)
        return response

    #############################
    # PURCHASE Mortgage Profile #
    #############################
    def test_update_purchase_returns_200(self):
        mp = self._create_mp(purchase=True)
        data = {
            'kind': MortgageProfile.PURCHASE,
            'property_occupation': 'my_current_residence',
            'is_veteran': None}
        expected = {
            'rate_preference': u'',
            'adjustable_rate_comfort': u'',
            'hoa_dues': None,
            'property_type': u'single_family',
            'id': mp.uuid,
            'property_state': u'',
            'target_value': None,
            'credit_score': None,
            'selected_lender_id': None,
            'advisor_email': u'',
            'purchase_down_payment': None,
            'purchase_type': u'',
            'selected_lender': None,
            'ownership_time': u'not_sure',
            'purchase_timing': u'',
            'kind': 'purchase',
            'property_occupation': u'my_current_residence',
            'referrer_email': u'',
            'property_county': u'',
            'property_zipcode': u'',
            'referral_url': u'',
            'conversion_url': u'',
            'is_veteran': None}
        response = self._update_mp(mp, data, purchase=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, expected)

    def test_get_purchase_returns_200(self):
        mp = self._create_mp(purchase=True)
        expected = {
            'rate_preference': u'',
            'adjustable_rate_comfort': u'',
            'hoa_dues': None,
            'property_type': u'single_family',
            'id': mp.uuid,
            'property_state': u'',
            'target_value': None,
            'credit_score': None,
            'selected_lender_id': None,
            'advisor_email': u'',
            'purchase_down_payment': None,
            'purchase_type': u'',
            'selected_lender': None,
            'ownership_time': u'not_sure',
            'purchase_timing': u'',
            'kind': 'purchase',
            'property_occupation': u'',
            'referrer_email': u'',
            'property_county': u'',
            'property_zipcode': u'',
            'referral_url': u'',
            'conversion_url': u'',
            'is_veteran': None}
        response = self._get_mp(mp, purchase=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, expected)

    def test_updating_a_purchase_with_a_loan_profile_returns_403(self):
        """Ensure we can create a new mortgage profile purchase object."""
        lp = loan_models.LoanProfileV1.objects.create()
        mp = self._create_mp(purchase=True)
        mp.loan_profilev1 = lp
        mp.save()
        data = {}
        self.assertEqual(self.client.session.keys(), [u'mortgage_profile_uuid', u'account_number'])
        response = self._update_mp(mp, data, purchase=True)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.session.keys(), [])

    def test_getting_a_purchase_with_a_loan_profile_returns_403(self):
        """Ensure we can create a new mortgage profile purchase object."""
        lp = loan_models.LoanProfileV1.objects.create()
        mp = self._create_mp(purchase=True)
        mp.loan_profilev1 = lp
        mp.save()
        self.assertEqual(self.client.session.keys(), [u'mortgage_profile_uuid', u'account_number'])
        response = self._get_mp(mp, purchase=True)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.session.keys(), [])

    #############################
    # REFINACE Mortgage Profile #
    #############################
    def test_update_refi_returns_200(self):
        mp = self._create_mp(purchase=False)
        data = {
            'kind': MortgageProfile.REFINANCE,
            'property_occupation': 'my_current_residence',
            'is_veteran': None}
        expected = {
            'cashout_amount': None,
            'rate_preference': u'',
            'adjustable_rate_comfort': u'',
            'hoa_dues': None,
            'property_type': u'single_family',
            'id': mp.uuid,
            'mortgage_monthly_payment': None,
            'property_state': u'',
            'selected_lender_id': None,
            'advisor_email': u'',
            'mortgage_owe': None,
            'selected_lender': None,
            'purpose': u'',
            'property_value': None,
            'mortgage_term': u'',
            'ownership_time': u'not_sure',
            'kind': 'refinance',
            'property_occupation': u'my_current_residence',
            'referrer_email': u'',
            'mortgage_start_date': None,
            'property_county': u'',
            'property_zipcode': u'',
            'credit_score': None,
            'referral_url': u'',
            'conversion_url': u'',
            'is_veteran': None}
        response = self._update_mp(mp, data, purchase=False)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, expected)

    def test_get_refi_returns_200(self):
        mp = self._create_mp(purchase=False)
        expected = {
            'cashout_amount': None,
            'rate_preference': u'',
            'adjustable_rate_comfort': u'',
            'hoa_dues': None,
            'property_type': u'single_family',
            'id': mp.uuid,
            'mortgage_monthly_payment': None,
            'property_state': u'',
            'selected_lender_id': None,
            'advisor_email': u'',
            'mortgage_owe': None,
            'selected_lender': None,
            'purpose': u'',
            'property_value': None,
            'mortgage_term': u'',
            'ownership_time': u'not_sure',
            'kind': 'refinance',
            'property_occupation': u'',
            'referrer_email': u'',
            'mortgage_start_date': None,
            'property_county': u'',
            'property_zipcode': u'',
            'credit_score': None,
            'referral_url': u'',
            'conversion_url': u'',
            'is_veteran': None}
        response = self._get_mp(mp, purchase=False)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(response.data, expected)

    def test_updating_a_refi_with_a_loan_profile_returns_403(self):
        """Ensure we can create a new mortgage profile purchase object."""
        lp = loan_models.LoanProfileV1.objects.create()
        mp = self._create_mp(purchase=False)
        mp.loan_profilev1 = lp
        mp.save()
        data = {}
        self.assertEqual(self.client.session.keys(), [u'mortgage_profile_uuid', u'account_number'])
        response = self._update_mp(mp, data, purchase=False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.session.keys(), [])

    def test_getting_a_refi_with_a_loan_profile_returns_403(self):
        """Ensure we can create a new mortgage profile purchase object."""
        lp = loan_models.LoanProfileV1.objects.create()
        mp = self._create_mp(purchase=False)
        mp.loan_profilev1 = lp
        mp.save()
        self.assertEqual(self.client.session.keys(), [u'mortgage_profile_uuid', u'account_number'])
        response = self._get_mp(mp, purchase=False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.session.keys(), [])
