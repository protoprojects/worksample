from django.db import connection
from django.core.urlresolvers import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from mortgage_profiles.factories import (
    MortgageProfilePurchaseFactory,
    MortgageProfileRefinanceFactory,
    RateQuoteRequestFactory,
    RateQuoteLenderFactory)
from mortgage_profiles.models import (
    MortgageProfile,
    MortgageProfileRefinance,
    MortgageProfilePurchase,
)


class MortgageProfileSubClassTests(APITestCase):
    def test_purchase_returns_purchase(self):
        mpp = MortgageProfilePurchaseFactory()
        mp = MortgageProfile.objects.get(id=mpp.id)
        self.assertIsInstance(mp, MortgageProfile)
        self.assertIsInstance(mp.subclass, MortgageProfilePurchase)

    def test_refi_returns_refi(self):
        mpp = MortgageProfileRefinanceFactory()
        mp = MortgageProfile.objects.get(id=mpp.id)
        self.assertIsInstance(mp, MortgageProfile)
        self.assertIsInstance(mp.subclass, MortgageProfileRefinance)


class MortgageProfileLoanAmountTests(TestCase):
    def test_cashout_refi_includes_cashout(self):
        mp = MortgageProfileRefinanceFactory(
            purpose=MortgageProfileRefinance.CASH_OUT,
            mortgage_owe=8000,
            cashout_amount=1000)
        self.assertEqual(mp.get_loan_amount(), 9000)

    def test_limited_refi_excludes_cashout(self):
        mp = MortgageProfileRefinanceFactory(
            purpose=MortgageProfileRefinance.LOWER_MORTGAGE_PAYMENTS,
            mortgage_owe=8000,
            cashout_amount=1000)
        self.assertEqual(mp.get_loan_amount(), 8000)

    def test_purchase_subtracts_downpayment(self):
        mp = MortgageProfilePurchaseFactory(
            target_value=8000,
            purchase_down_payment=1000)
        self.assertEqual(mp.get_loan_amount(), 7000)


class PropertyUsageMappingTests(APITestCase):
    def test_purchase_type_mapping(self):
        mpp = MortgageProfilePurchaseFactory(property_occupation='my_current_residence')
        self.assertEqual(mpp.mismo_property_usage, 'PrimaryResidence')
        mpp = MortgageProfilePurchaseFactory(property_occupation='second_home_vacation_home')
        self.assertEqual(mpp.mismo_property_usage, 'SecondHome')
        mpp = MortgageProfilePurchaseFactory(property_occupation='investment_property')
        self.assertEqual(mpp.mismo_property_usage, 'Investor')

    def test_purchase_mismo_to_property_occupation(self):
        value = MortgageProfilePurchase.mismo_to_sample_property_occupation('PrimaryResidence')
        self.assertEqual(value, 'my_current_residence')
        value = MortgageProfilePurchase.mismo_to_sample_property_occupation('SecondHome')
        self.assertEqual(value, 'second_home_vacation_home')
        value = MortgageProfilePurchase.mismo_to_sample_property_occupation('Investor')
        self.assertEqual(value, 'investment_property')

    def test_refi_property_occupation_mapping(self):
        mpp = MortgageProfileRefinanceFactory(property_occupation='my_current_residence')
        self.assertEqual(mpp.mismo_property_usage, 'PrimaryResidence')
        mpp = MortgageProfileRefinanceFactory(property_occupation='second_home_vacation_home')
        self.assertEqual(mpp.mismo_property_usage, 'SecondHome')
        mpp = MortgageProfileRefinanceFactory(property_occupation='investment_property')
        self.assertEqual(mpp.mismo_property_usage, 'Investor')

    def test_refi_mismo_property_usage(self):
        value = MortgageProfileRefinance.mismo_to_sample_property_occupation('PrimaryResidence')
        self.assertEqual(value, 'my_current_residence')
        value = MortgageProfileRefinance.mismo_to_sample_property_occupation('SecondHome')
        self.assertEqual(value, 'second_home_vacation_home')
        value = MortgageProfileRefinance.mismo_to_sample_property_occupation('Investor')
        self.assertEqual(value, 'investment_property')


#################################
# selected_rate_quote_lender tests #
#################################
class MortgageProfileSelectRateQuoteLenderMixin(object):
    KIND = None
    FACTORY = None

    def setUp(self):
        # pylint: disable=not-callable
        self.mortgage_profile = self.FACTORY()
        rate_quote_request = RateQuoteRequestFactory(mortgage_profile=self.mortgage_profile)
        self.rate_quote_lender = RateQuoteLenderFactory(request=rate_quote_request)
        self.url = reverse('mortgage_profiles:{0}_details'.format(self.KIND),
                           kwargs={'uuid': self.mortgage_profile.uuid})
        session = self.client.session
        session['mortgage_profile_uuid'] = self.mortgage_profile.uuid
        session.save()

    def test_patch_fails_with_non_existing_rate_quote_lender(self):
        cursor = connection.cursor()
        invalid_pk = cursor.execute('SELECT MAX(id)+1 FROM mortgage_profiles_ratequotelender') or 99
        response = self.client.patch(self.url, data={'selected_lender_id': invalid_pk})
        expected = {'selected_lender_id': [u'Invalid pk "{0}" - object does not exist.'.format(invalid_pk)]}
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, expected)

    def test_patch_fails_with_non_related_rate_quote_lender(self):
        rate_quote_lender = RateQuoteLenderFactory()
        response = self.client.patch(self.url, data={'selected_lender_id': rate_quote_lender.pk})
        expected = {'selected_lender_id': [u'Invalid pk "{0}" - object does not exist.'.format(rate_quote_lender.pk)]}
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, expected)

    def test_patch_fails_with_non_unique_rate_quote_lender_reference(self):
        # pylint: disable=not-callable
        self.FACTORY(selected_rate_quote_lender=self.rate_quote_lender)
        response = self.client.patch(self.url, data={'selected_lender_id': self.rate_quote_lender.pk})

        expected = {'selected_lender_id': [
            'This field must be unique.  '
            'Another mortgage_profile already references this rate_quote_lender.']}
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, expected)

    def test_patch_success_with_valid_rate_quote_lender(self):
        response = self.client.patch(self.url, data={'selected_lender_id': self.rate_quote_lender.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['selected_lender_id'], self.rate_quote_lender.pk)
        self.assertEqual(response.data['selected_lender']['id'], self.rate_quote_lender.id)
        self.assertEqual(response.data['selected_lender']['monthly_payment'], self.rate_quote_lender.monthly_payment)

    def test_property_county_name_removes_county(self):
        """Ensure county name does not include 'County'"""
        # pylint: disable=not-callable
        profile = self.FACTORY(property_county='Washtenaw County',
                               property_state='Michigan',
                               property_zipcode='48103')
        self.assertEqual(profile.property_county, 'Washtenaw County')
        self.assertEqual(profile.property_county_name, 'Washtenaw')

    def test_property_county_name_works_with_null(self):
        """Ensure county name does not include 'County'"""
        # pylint: disable=not-callable
        profile = self.FACTORY.build(property_county=None,
                                     property_state='Michigan',
                                     property_zipcode='48103')
        self.assertIsNone(profile.property_county)
        self.assertEqual(profile.property_county_name, '')

    def test_property_county_name_works_with_blank(self):
        """Ensure county name does not include 'County'"""
        # pylint: disable=not-callable
        profile = self.FACTORY(property_county='',
                               property_state='Michigan',
                               property_zipcode='48103')
        self.assertEqual(profile.property_county, '')
        self.assertEqual(profile.property_county_name, '')


class PurchaseSelectRateQuoteLenderTests(MortgageProfileSelectRateQuoteLenderMixin, APITestCase):
    KIND = 'purchase'
    FACTORY = MortgageProfilePurchaseFactory


class RefinanceSelectRateQuoteLenderTests(MortgageProfileSelectRateQuoteLenderMixin, APITestCase):
    KIND = 'refinance'
    FACTORY = MortgageProfileRefinanceFactory
