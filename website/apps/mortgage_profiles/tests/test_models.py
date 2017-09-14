from decimal import Decimal, InvalidOperation
import logging

from mock import patch

from django.test import TestCase

from core.utils import LogMutingTestMixinBase
from mortgage_profiles.factories import (
    MortgageProfilePurchaseFactory, MortgageProfileRefinanceFactory, RateQuoteLenderFactory, RateQuoteRequestFactory)

logger = logging.getLogger('sample.mortech.test')


class MortechMutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.mortech.api',
                 'sample.mortech.fees',
                 'sample.mortech.calculations',
                 'sample.mortgage_profiles']


class RateQuoteRequestTestCase(MortechMutingMixin, TestCase):
    def setUp(self):
        self.profile = MortgageProfilePurchaseFactory(ownership_time='medium_term')
        self.request = RateQuoteRequestFactory(mortgage_profile=self.profile)
        self.lender = RateQuoteLenderFactory(request=self.request)
        super(RateQuoteRequestTestCase, self).setUp()

    def test_get_rate_quote_success(self):
        """Should return the single best rate."""
        result = self.request.get_rate_quote()

        self.assertEqual(result, self.lender)

    def test_get_scenarios_success(self):
        """Should return all appropriate lenders."""
        results = self.request.get_scenarios()

        self.assertIn(self.lender, results)

    def test_get_scenarios_failure(self):
        """Should return any exceptions."""
        lender = RateQuoteLenderFactory()
        results = self.request.get_scenarios()

        self.assertNotIn(lender, results)

    def test_get_scenarios_results(self):
        RateQuoteLenderFactory(request=self.request, rate=275.0, points=1.0)
        RateQuoteLenderFactory(request=self.request, rate=262.5, points=0.5)
        lender3 = RateQuoteLenderFactory(request=self.request, rate=262.5, points=-0.50)
        lender4 = RateQuoteLenderFactory(request=self.request, rate=275.0, points=-1.0)

        results = self.request.get_scenarios()

        self.assertIn(lender3, results)
        self.assertIn(lender4, results)
        self.assertIn(self.lender, results)

    def test_get_rate_quote_returns_nearest_par(self):
        """Return best rate among top 5 with credits closest to par"""
        profile = MortgageProfilePurchaseFactory(ownership_time='medium_term')
        request = RateQuoteRequestFactory(mortgage_profile=profile)
        # has a fee, not selected
        RateQuoteLenderFactory(request=request, rate=200.0, points='0.1')
        # the top 5
        RateQuoteLenderFactory(request=request, rate=250.0, points='0.0')
        RateQuoteLenderFactory(request=request, rate=220.0, points='-0.1')
        RateQuoteLenderFactory(request=request, rate=210.0, points='-0.2',
                               lender_name='Best Lender')
        RateQuoteLenderFactory(request=request, rate=210.0, points='-0.3')
        RateQuoteLenderFactory(request=request, rate=210.0, points='-0.4')
        # out of the top 5 credits closest to par, not selected
        RateQuoteLenderFactory(request=request, rate=200.0, points='-0.5')

        lender = request.get_rate_quote()

        self.assertEqual(lender.rate, 210.0)
        self.assertEqual(lender.points, Decimal('-0.2'))
        self.assertEqual(lender.lender_name, 'Best Lender')

    def test_get_rate_quote_with_rate(self):
        """Should return the best priced lender for a given rate."""
        RateQuoteLenderFactory(request=self.request, rate=262.5, points=1.0)
        RateQuoteLenderFactory(request=self.request, rate=262.5, points=0.5)
        RateQuoteLenderFactory(request=self.request, rate=262.5, points=-0.50)
        lender4 = RateQuoteLenderFactory(request=self.request, rate=262.5, points=-1.0)

        results = self.request.get_rate_quote(rate=262.5)

        self.assertEqual(lender4, results)

    def test_get_lender_by_rate(self):
        """Should return best priced lender by rate."""
        RateQuoteLenderFactory(request=self.request, rate=250.0, points=1.0)
        RateQuoteLenderFactory(request=self.request, rate=262.5, points=0.5)
        RateQuoteLenderFactory(request=self.request, rate=250.0, points=-0.50)
        lender4 = RateQuoteLenderFactory(request=self.request, rate=262.5, points=-1.0)

        results = self.request.get_lender_by_rate(rate=262.5, term='15 Year', amortization='Fixed')

        self.assertEqual(lender4, results)

    def test_has_lenders(self):
        """Should return whether any lenders are available for the request."""
        request = RateQuoteRequestFactory(mortgage_profile=self.profile)
        self.assertFalse(request.has_lenders)
        RateQuoteLenderFactory(request=request)
        self.assertTrue(request.has_lenders)

    def test_has_lender_product(self):
        """Should return whether lenders with specific products are available for the request."""
        request = RateQuoteRequestFactory(mortgage_profile=self.profile)
        term, amortization = ('30 Year', 'Fixed')

        self.assertFalse(request.has_lender_product(term, amortization))
        RateQuoteLenderFactory(request=request, term=term, amortization_type=amortization)
        self.assertTrue(request.has_lender_product(term, amortization))


class RateQuoteLenderTestCase(MortechMutingMixin, TestCase):
    def setUp(self):
        fees = {
            'Title Fee': 10.0,
            'Flood Certification': 10.0,
            'Trust Review Fee': 10.0,
            'Estimated Appraisal Fee': 10.0,
            'Escrow Fee': 10.0,
            'Credit Report': 10.0,
            'Tax Service Fee': 10.0,
            'Admin Fee': 10.0,
            'Pre-paid Interest': 10.0,
        }
        self.lender = RateQuoteLenderFactory(fees=fees)
        super(RateQuoteLenderTestCase, self).setUp()

    def test_lender_decimal_fields(self):
        """Should return exception when too many digits submitted for decimal fields."""
        with self.assertRaises(InvalidOperation):
            RateQuoteLenderFactory(rate=10000.000)

    def test_lender_credit_report_fees(self):
        """Should return Credit Report fee or default fee when not available."""
        self.assertEqual(self.lender.credit_report_fee, 10.0)
        self.lender.fees.pop('Credit Report')
        self.assertEqual(self.lender.credit_report_fee, 0.0)

    def test_lender_monthly_payment(self):
        """Should calculate monthly payment and return it."""
        lender = RateQuoteLenderFactory()
        self.assertEqual(lender.monthly_payment, 800.0)
        lender.monthly_premium = 0.0
        self.assertEqual(lender.monthly_payment, 1200.0)

    def test_lender_prepaid_interest(self):
        self.assertEqual(self.lender.prepaid_interest, 10.0)
        self.lender.fees.pop('Pre-paid Interest')
        self.assertEqual(self.lender.prepaid_interest, 0.0)

    def test_lender_tax_service_fee(self):
        self.assertEqual(self.lender.tax_service_fee, 10.0)
        self.lender.fees.pop('Tax Service Fee')
        self.assertEqual(self.lender.tax_service_fee, 69.0)

    def test_lender_flood_certification(self):
        self.assertEqual(self.lender.flood_certification, 10.0)
        self.lender.fees.pop('Flood Certification')
        self.assertEqual(self.lender.flood_certification, 0.0)

    def test_lender_trust_review_fee(self):
        self.assertEqual(self.lender.trust_review_fee, 10.0)
        self.lender.fees.pop('Trust Review Fee')
        self.assertEqual(self.lender.trust_review_fee, 0.0)

    def test_lender_estimated_appraisal_fee(self):
        self.assertEqual(self.lender.estimated_appraisal_fee, 10.0)
        self.lender.fees.pop('Estimated Appraisal Fee')
        self.assertEqual(self.lender.estimated_appraisal_fee, 550.0)

    def test_lender_title_fee(self):
        self.assertEqual(self.lender.title_fee, 10.0)
        self.lender.fees.pop('Title Fee')
        self.assertEqual(self.lender.title_fee, 0.0)

    def test_lender_escrow_fee(self):
        self.assertEqual(self.lender.escrow_fee, 10.0)
        self.lender.fees.pop('Escrow Fee')
        self.assertEqual(self.lender.escrow_fee, 0.0)

    def test_lender_underwriting_fee(self):
        self.assertEqual(self.lender.underwriting_fee, 10.0)
        self.lender.fees.pop('Admin Fee')
        self.assertEqual(self.lender.underwriting_fee, 0.0)


class MortgageProfileTestCase(MortechMutingMixin, TestCase):
    def setUp(self):
        self.profile = MortgageProfilePurchaseFactory(ownership_time='medium_term')
        self.request = RateQuoteRequestFactory(mortgage_profile=self.profile)
        self.lender = RateQuoteLenderFactory(term='15 Year', amortization_type='Fixed', request=self.request)
        super(MortgageProfileTestCase, self).setUp()

    @patch("mortgage_profiles.models.RateQuoteRequest.get_lender_by_rate")
    def test_update_selected_lender(self, mock_get_lender_by_rate):
        """Should updated selected_rate_quote_lender to newest lender with same term, amort and rate."""
        self.profile.selected_rate_quote_lender = self.lender
        new_request = RateQuoteRequestFactory(mortgage_profile=self.profile)
        par_lender = RateQuoteLenderFactory(term='15 Year', amortization_type='Fixed', request=new_request)
        mock_get_lender_by_rate.return_value = par_lender

        self.profile.update_selected_lender()

        self.assertEqual(par_lender, self.profile.selected_rate_quote_lender)

    @patch("mortgage_profiles.models.RateQuoteRequest.get_lender_by_rate")
    def test_no_update_selected_lender(self, mock_get_lender_by_rate):
        """Should not update selected_rate_quote_lender when the request has no lenders."""
        self.profile.selected_rate_quote_lender = self.lender
        new_request = RateQuoteRequestFactory(mortgage_profile=self.profile)
        mock_get_lender_by_rate.return_value = None

        result = self.profile.update_selected_lender()
        self.assertFalse(new_request.has_lenders)
        self.assertEqual(result, None)


class RateQuoteLenderTest(TestCase):
    def test_is_variable_returns_false_for_fixed(self):
        rate_quote_lender = RateQuoteLenderFactory(amortization_type='Fixed')
        self.assertFalse(rate_quote_lender.is_variable())
        self.assertTrue(rate_quote_lender.is_fixed())

    def test_is_variable_returns_true_for_variable(self):
        rate_quote_lender = RateQuoteLenderFactory(amortization_type='Variable')
        self.assertTrue(rate_quote_lender.is_variable())
        self.assertFalse(rate_quote_lender.is_fixed())

    def test_mismo_fnm_product_plan_identifier_returns_none_for_fixed(self):
        rate_quote_lender = RateQuoteLenderFactory(amortization_type='Fixed', term='5 Year')
        self.assertIsNone(rate_quote_lender.mismo_fnm_product_plan_identifier())

    def test_mismo_fnm_product_plan_identifier_returns_identifier_for_variable(self):
        yr_3 = RateQuoteLenderFactory(amortization_type='Variable', term='3 Year')
        yr_5 = RateQuoteLenderFactory(amortization_type='Variable', term='5 Year')
        yr_7 = RateQuoteLenderFactory(amortization_type='Variable', term='7 Year')
        self.assertEqual(yr_3.mismo_fnm_product_plan_identifier(), None)
        self.assertEqual(yr_5.mismo_fnm_product_plan_identifier(), 'GEN5')
        self.assertEqual(yr_7.mismo_fnm_product_plan_identifier(), 'GEN7')


class MortgageProfileRefinanceTestCase(TestCase):
    def test_get_loan_profile_purpose_of_refi_mapping(self):
        mp_1 = MortgageProfileRefinanceFactory(purpose='lower_mortgage_payments')
        mp_2 = MortgageProfileRefinanceFactory(purpose='cash_out')
        mp_3 = MortgageProfileRefinanceFactory(purpose='heloc')
        mp_4 = MortgageProfileRefinanceFactory(purpose='both')

        self.assertEqual(mp_1.get_loan_profile_purpose_of_refi(), 'rate_or_term')
        self.assertEqual(mp_2.get_loan_profile_purpose_of_refi(), 'cash_out_other')
        self.assertEqual(mp_3.get_loan_profile_purpose_of_refi(), None)
        self.assertEqual(mp_4.get_loan_profile_purpose_of_refi(), 'cash_out_other')
