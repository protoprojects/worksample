import logging
from mock import patch
from httmock import with_httmock
from requests.exceptions import ConnectionError, HTTPError, Timeout

from django.test import TestCase

from core.utils import LogMutingTestMixinBase
from mortgage_profiles.utils import MortechResponse
from mortgage_profiles.factories import (
    MortgageProfilePurchaseFactory,
    RateQuoteLenderFactory,
    RateQuoteRequestFactory
)
from mortgage_profiles.models import MortgageProfilePurchase
from mortgage_profiles import mortech
from mortgage_profiles.mocks import (
    mortech_response_success,
    mortech_response_status_code_408,
    mortech_response_status_code_503,
    mortech_response_status_code_400,
    mortech_response_blank,
    mortech_response_no_results,
    mortech_response_timeout,
    mortech_response_connection_error
)

logger = logging.getLogger('sample.mortech.test')


class MortechMutingMixin(LogMutingTestMixinBase):
    log_names = [
        'sample.mortech.api',
        'sample.mortech.fees',
        'sample.mortech.calculations',
        'sample.mortgage_profiles'
    ]


class RateQuoteApiPurchaseTestCase(MortechMutingMixin, TestCase):
    """Tests for mortech purchase request/response data"""
    def setUp(self):
        self.mortgage_profile = MortgageProfilePurchaseFactory(
            property_occupation='my_current_residence')
        self.api = mortech.MortechApi(mortgage_profile=self.mortgage_profile)
        super(RateQuoteApiPurchaseTestCase, self).setUp()

    def test_initial_data_valid(self):
        data = self.api.get_initial_data()
        expected = {
            'fico': 850,
            'loan_amount': 600000,
            'loanpurpose': 0,
            'occupancy': 0,
            'propertyCounty': 'Secret county',
            'propertyState': 'CA',
            'propType': 0,
        }
        for key, value in expected.iteritems():
            message = '{0} ({1}) is not equal to {2}'.format(data.get(key), key, value)
            self.assertEqual(data.get(key), value, msg=message)

    def test_calculations_class(self):
        calculations = self.api.get_calculations()
        self.assertEqual(calculations.__class__, mortech.MortechCalculationsPurchase)

    @with_httmock(mortech_response_success)
    def test_response_content_valid(self):
        self.assertEqual(mortech_response_success.call, {'count': 0, 'called': False})
        response = self.api.get_response()
        self.assertTrue(response.is_valid())
        self.assertEqual(mortech_response_success.call, {'count': 1, 'called': True})

    def test_response_content_invalid(self):
        self.mortgage_profile.credit_score = None
        self.assertFalse(self.api.is_valid())
        self.assertTrue(self.api.get_errors())

    def test_response_state_no_allowed(self):
        self.mortgage_profile.property_state = 'State Not Supported'
        self.assertFalse(self.api.is_valid())
        self.assertTrue(self.api.get_errors())

    def test_property_types(self):
        profile = self.mortgage_profile
        ls_property = mortech.calculations.MortechCalculationsPurchase(profile)
        for k, v in mortech.MortechCalculationsPurchase.PROPERTY_TYPE_MAPPING.items():
            profile.property_type = k
            self.assertEqual(ls_property.get_property_type(), v)
            if profile.property_type.startswith('condo'):
                self.assertTrue(ls_property.is_condo())
            else:
                self.assertFalse(ls_property.is_condo())

    @with_httmock(mortech_response_blank)
    def test_get_response_no_content_exception(self):
        self.assertEqual(mortech_response_blank.call, {'count': 0, 'called': False})
        try:
            self.api.get_response()
            self.assertTrue(False, 'Not raised Exception for get_response')
        except Exception as exc:
            self.assertEqual(exc.message, 'Mortech response is missing content.')
        self.assertEqual(mortech_response_blank.call, {'count': 1, 'called': True})

    @with_httmock(mortech_response_status_code_400)
    def test_get_response_status_code_400(self):
        self.assertEqual(mortech_response_status_code_400.call, {'count': 0, 'called': False})
        try:
            self.api.get_response()
            self.assertTrue(False, 'Not raised HTTPError for get_response')
        except HTTPError as exc:
            self.assertTrue(exc.message.startswith('400 Client Error:'))
        self.assertEqual(mortech_response_status_code_400.call, {'count': 1, 'called': True})

    @with_httmock(mortech_response_status_code_408)
    def test_get_response_status_code_408(self):
        self.assertEqual(mortech_response_status_code_408.call, {'count': 0, 'called': False})
        try:
            self.api.get_response()
            self.assertTrue(False, 'Not raised HTTPError for get_response')
        except HTTPError as exc:
            self.assertTrue(exc.message.startswith('408 Client Error:'))
        self.assertEqual(mortech_response_status_code_408.call, {'count': 1, 'called': True})

    @with_httmock(mortech_response_status_code_503)
    def test_get_response_status_code_503(self):
        self.assertEqual(mortech_response_status_code_503.call, {'count': 0, 'called': False})
        try:
            self.api.get_response()
            self.assertTrue(False, 'Not raised HTTPError for get_response')
        except HTTPError as exc:
            self.assertTrue(exc.message.startswith('503 Server Error:'))
        self.assertEqual(mortech_response_status_code_503.call, {'count': 1, 'called': True})

    @with_httmock(mortech_response_timeout)
    def test_get_response_timeout_exception(self):
        self.assertEqual(mortech_response_timeout.call, {'count': 0, 'called': False})
        with self.assertRaises(Timeout):
            self.api.get_response()
        self.assertEqual(mortech_response_timeout.call, {'count': 1, 'called': True})

    @with_httmock(mortech_response_connection_error)
    def test_get_response_connection_error_exception(self):
        self.assertEqual(mortech_response_connection_error.call, {'count': 0, 'called': False})
        with self.assertRaises(ConnectionError):
            self.api.get_response()
        self.assertEqual(mortech_response_connection_error.call, {'count': 1, 'called': True})

    @with_httmock(mortech_response_success)
    @patch('mortgage_profiles.mortech.MortechApi.save_lenders')
    def test_get_response_success(self, mock_save_lenders):
        """Should call save_lenders if response contains results."""
        self.assertEqual(mortech_response_success.call, {'count': 0, 'called': False})
        api = mortech.MortechApi(mortgage_profile=self.mortgage_profile)
        result = api.get_response()
        self.assertTrue(isinstance(result, MortechResponse))
        mock_save_lenders.assert_called_once()
        self.assertEqual(mortech_response_success.call, {'count': 1, 'called': True})

    @with_httmock(mortech_response_no_results)
    def test_get_response_no_results(self):
        """Should return error if response is successful but contains no results."""
        self.assertEqual(mortech_response_no_results.call, {'count': 0, 'called': False})
        response = {'error_num': '0', 'error_desc': 'Success'}
        results = self.api.get_response()
        self.assertEqual(results.get_errors(), response)
        self.assertEqual(mortech_response_no_results.call, {'count': 3, 'called': True})


class MortechCalculationTestCase(MortechMutingMixin, TestCase):
    """Tests for request Mortech data made from mortgage profile"""

    def test_calculations_occupation(self):
        mp = MortgageProfilePurchaseFactory(
            property_occupation=MortgageProfilePurchase.PROPERTY_OCCUPATION_CHOICES.primary)
        calculations = mortech.MortechCalculationsPurchase(mp)
        self.assertEqual(calculations.get_loan_amount(), 600000)
        self.assertEqual(calculations.get_cashout_amount(), None)
        self.assertEqual(calculations.get_occupancy_type(), 0)
        mp.property_occupation = MortgageProfilePurchase.PROPERTY_OCCUPATION_CHOICES.investment
        self.assertEqual(calculations.get_occupancy_type(), 1)
        mp.property_occupation = MortgageProfilePurchase.PROPERTY_OCCUPATION_CHOICES.secondary
        self.assertEqual(calculations.get_occupancy_type(), 2)


class MortechScenarioTestCase(MortechMutingMixin, TestCase):
    """Tests for manipulations with Mortech response"""
    def setUp(self):
        self.mortgage_profile = MortgageProfilePurchaseFactory()
        self.scenario = mortech.MortechScenarioPurchase(self.mortgage_profile)
        self.request = RateQuoteRequestFactory(mortgage_profile=self.mortgage_profile)
        self.lender = RateQuoteLenderFactory(request=self.request)
        super(MortechScenarioTestCase, self).setUp()

    def test_is_valid(self):
        results = [self.lender.request, self.lender, self.mortgage_profile.ownership_time]
        for item in results:
            message = '{0} is none.'.format(item)
            self.assertIsNotNone(item, msg=message)

    def test_calculate(self):
        """Should return queryset of lenders."""
        request = RateQuoteRequestFactory(mortgage_profile=self.mortgage_profile)
        lender = RateQuoteLenderFactory(request=request, program_name="ABC Loan")

        results = self.scenario.calculate(term='15 Year', amortization_type='Fixed')
        message = '{0} is not in {1}'.format(lender, results)
        self.assertEqual(lender, results, msg=message)

    def test_calculate_adjust_filter(self):
        """Should filter out all available lenders."""
        request = RateQuoteRequestFactory(mortgage_profile=self.mortgage_profile)
        lender = RateQuoteLenderFactory(request=request, points=1.0, program_name="Hi Loan")
        # Should adjust filter to return points > 0.0
        results = self.scenario.calculate(term='15 Year', amortization_type='Fixed')
        message = '{0} is not in {1}'.format(lender, results)
        self.assertEqual(lender, results, msg=message)
        # Should filter to return points <= 0.0
        lender2 = RateQuoteLenderFactory(request=request, program_name="Lo Loan")
        results = self.scenario.calculate(term='15 Year', amortization_type='Fixed')
        self.assertEqual(lender2, results, msg=message)

    def test_calculate_va(self):
        """Should return queryset of VA lenders."""
        profile = MortgageProfilePurchaseFactory(purchase_down_payment=5000, target_value=60000)
        request = RateQuoteRequestFactory(mortgage_profile=profile)
        RateQuoteLenderFactory(program_type='VA', request=request)
        scenario = mortech.MortechScenarioPurchase(profile)
        rate_quote_request = profile.rate_quote_requests.first()
        queryset = rate_quote_request.rate_quote_lenders.filter(term='15 Year', amortization_type='Fixed')
        message = "{0} is not VA suitable.".format(profile)
        self.assertTrue(scenario.is_va_suitable(queryset), msg=message)

    def test_calculate_fha(self):
        """Should return queryset of FHA lenders."""
        profile = MortgageProfilePurchaseFactory(purchase_down_payment=1000, target_value=60000)
        request = RateQuoteRequestFactory(mortgage_profile=profile)
        RateQuoteLenderFactory(program_name='FHA Loan', program_type='FHA', request=request)
        scenario = mortech.MortechScenarioPurchase(profile)

        queryset = profile.rate_quote_requests.first().rate_quote_lenders.filter(term='15 Year', amortization_type='Fixed')
        message = "{0} is not FHA suitable.".format(profile)
        self.assertTrue(scenario.is_fha_suitable(queryset), msg=message)

    def test_calculate_conf(self):
        """Should return queryset of Conforming lenders."""
        profile = MortgageProfilePurchaseFactory(purchase_down_payment=50000, target_value=60000)
        request = RateQuoteRequestFactory(mortgage_profile=profile)
        RateQuoteLenderFactory(program_name='Conf Loan', program_type='Conf', request=request)
        scenario = mortech.MortechScenarioPurchase(profile)
        rate_quote_request = profile.rate_quote_requests.first()
        queryset = rate_quote_request.rate_quote_lenders.filter(term='15 Year', amortization_type='Fixed')
        message = "{0} is not Conf suitable.".format(queryset)
        self.assertTrue(scenario.is_conf_suitable(queryset), msg=message)

    def test_calculate_conf_jumbo(self):
        """Should return queryset of Conforming lenders."""
        profile = MortgageProfilePurchaseFactory(purchase_down_payment=50000, target_value=60000)
        request = RateQuoteRequestFactory(mortgage_profile=profile)
        RateQuoteLenderFactory(program_type='Conforming', program_name='Jumbo Conforming', request=request)
        scenario = mortech.MortechScenarioPurchase(profile)
        rate_quote_request = profile.rate_quote_requests.first()
        queryset = rate_quote_request.rate_quote_lenders.filter(term='15 Year', amortization_type='Fixed')
        message = "{0} is not Jumbo Conf suitable.".format(profile)
        self.assertTrue(scenario.is_conf_jumbo_suitable(queryset), msg=message)
