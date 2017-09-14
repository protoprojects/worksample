from mock import patch
from httmock import with_httmock

from django.core.urlresolvers import reverse

from rest_framework.test import APITestCase, APIRequestFactory

from core.utils import LogMutingTestMixinBase
from mortgage_profiles.factories import (
    RateQuoteLenderFactory,
    MortgageProfilePurchaseFactory,
    RateQuoteRequestFactory)
from mortgage_profiles.models import MortgageProfile
from mortgage_profiles.serializers import RateQuoteLenderSerializer
from mortgage_profiles.mocks import mortech_response_success


# Test request data
PURCHASE_REQUEST = 'kind=purchase&' \
                   'propertyState=California&' \
                   'propertyCity=San Francisco&' \
                   'propertyZipcode=94111&' \
                   'propertyCounty=San Francisco&' \
                   'propertyValue=500000&' \
                   'purchaseTiming=researching_options&' \
                   'ownershipTime=medium_term&' \
                   'purchaseDownPayment=100000&' \
                   'referralUrl=http://localhost:8000&' \
                   'conversionUrl=http://localhost:8000&' \
                   'purchaseType=first_time_homebuyer&' \
                   'creditScore=760&' \
                   'isVeteran=False&' \
                   'propertyOccupation=primary&' \
                   'propertyType=single_family'

PURCHASE_MIN_REQUEST = 'propertyState=California&' \
                       'propertyCity=San%20Francisco&' \
                       'kind=purchase&' \
                       'propertyValue=500000&' \
                       'creditScore=760&' \
                       'purchaseDownPayment=100000'

REFINANCE_REQUEST = 'kind=refinance&' \
                   'propertyType=single_family&' \
                   'propertyState=California&' \
                   'propertyCity=San Francisco&' \
                   'propertyZipcode=94111&' \
                   'propertyCounty=San Francisco&' \
                   'propertyValue=500000&' \
                   'ownershipTime=long_term&' \
                   'isVeteran=false&' \
                   'referralUrl=http://localhost:8000&' \
                   'conversionUrl=http://localhost:8000&' \
                   'propertyOccupation=0&' \
                   'creditScore=760&' \
                   'ratePreference=fixed&' \
                   'purpose=lower_mortgage_payments&' \
                   'mortgageOwe=250000&' \
                   'mortgageTerm=30_year&' \
                   'mortgageMonthly_payment=1000&' \
                   'cashoutAmount=10000'

REFINANCE_MIN_REQUEST = 'kind=refinance&' \
                       'propertyState=California&' \
                       'propertyValue=500000&' \
                       'propertyOccupation=0&' \
                       'creditScore=760&' \
                       'purpose=lower_mortgage_payments&' \
                       'mortgageOwe=250000'


class MortechMutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.mortech.api',
                 'sample.mortech.fees',
                 'sample.mortech.calculations',
                 'sample.mortech.results',
                 'sample.core.parsers',
                 'sample.mortgage_profiles']


class RateQuoteViewsTestCase(MortechMutingMixin, APITestCase):
    """Should return 200 if uuid is found and return results."""
    def setUp(self):
        self.uuid = 'MrZV8ChTc4L5tv66o7B65f'
        self.profile = MortgageProfilePurchaseFactory(ownership_time='medium_term')
        self.request = RateQuoteRequestFactory(uuid=self.uuid, mortgage_profile=self.profile)
        self.lender = RateQuoteLenderFactory(request=self.request)
        super(RateQuoteViewsTestCase, self).setUp()

    @patch("mortgage_profiles.models.RateQuoteRequest.get_scenarios")
    @patch("mortgage_profiles.models.RateQuoteRequest.get_par_lender")
    def test_get_results_success(self, mocked_get_par_lender, mocked_get_scenarios):
        """Should return a response object with par_lender and scenarios."""
        data = {'term': 'Fixed', 'amortizationType': '30 Year'}
        url = reverse('mortgage_profiles:rate_quote', args=[self.uuid])

        lender1 = RateQuoteLenderFactory(request=self.request, rate=200.0)
        lender2 = RateQuoteLenderFactory(request=self.request, points=-1.0)
        lenders = [self.lender, lender1, lender2]
        lenders_data = RateQuoteLenderSerializer(lenders, many=True).data
        par_lender = RateQuoteLenderSerializer(self.lender).data

        mocked_get_scenarios.return_value = lenders
        mocked_get_par_lender.return_value = self.lender

        response = self.client.get(url, data=data)
        response_no_query = self.client.get(url)
        results = {
            'par_lender': par_lender,
            'request_uuid': self.uuid,
            'results': lenders_data,
            'term': par_lender['term'],
            'amortization_type': par_lender['amortization_type']
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_no_query.status_code, 200)
        self.assertEqual(response.data, results)
        self.assertEqual(response_no_query.data, results)

    def test_get_results_failure(self):
        """Should return 404 if the uuid is not found."""
        uuid = 'MrZV8ChTc4L5tv66o7B65x'

        url = reverse('mortgage_profiles:rate_quote', args=[uuid])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    @with_httmock(mortech_response_success)
    @patch("mortgage_profiles.models.RateQuoteRequest.get_par_lender")
    def test_get_unique_results_success(self, mocked_get_par_lender):
        self.assertEqual(mortech_response_success.call, {'count': 0, 'called': False})
        lender1 = RateQuoteLenderFactory(request=self.request, term='30 Year', amortization_type='Fixed')
        lender2 = RateQuoteLenderFactory(request=self.request, term='7 Year', amortization_type='Variable')
        lender3 = RateQuoteLenderFactory(request=self.request, term='5 Year', amortization_type='Variable')
        lenders = [self.lender, lender1, lender2, lender3]
        lenders_data = RateQuoteLenderSerializer(lenders, many=True).data

        mocked_get_par_lender.side_effect = lenders
        url = reverse('mortgage_profiles:rate_quote_request')
        response = self.client.post(
            url,
            data=PURCHASE_REQUEST,
            content_type='application/x-www-form-urlencoded'
        )
        results = {
            'request_uuid': response.data['request_uuid'],
            'results': lenders_data
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(results, response.data)
        self.assertEqual(mortech_response_success.call, {'count': 1, 'called': True})

    def test_rate_quote_request_data_invalid(self):
        """Should return 400 when invalid/incomplete data submitted."""
        invalid_data = 'kind=purchase&' \
                       'propertyState=California'

        url = reverse('mortgage_profiles:rate_quote_request')
        response = self.client.post(url,
                                    data=invalid_data,
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 400)


class RateQuoteViewTests(MortechMutingMixin, APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        super(RateQuoteViewTests, self).setUp()

    def test_get_rate_quote_view_without_uuid_in_session_returns_404(self):
        url = reverse('mortgage_profiles:rate_quote_service')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_rate_quote_view_with_invalid_uuid_in_session_returns_404(self):
        # set the mortgage_profile_uuid in the session
        url = reverse('mortgage_profiles:refinance_list')
        response = self.client.post(url, data={'kind': MortgageProfile.PURCHASE})
        self.assertEqual(response.status_code, 201)

        # show that the response is 400 to start
        url = reverse('mortgage_profiles:rate_quote_service')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

        # when updating to an new uuid the response changes to a 404
        new_uuid = 'MrZV8ChTc4L5tv66o7B65f'
        uuid = self.client.session.get('mortgage_profile_uuid')
        mp = MortgageProfile.objects.get(uuid=uuid)
        mp.uuid = new_uuid
        mp.save()
        url = reverse('mortgage_profiles:rate_quote_service')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_rate_quote_view_with_insufficient_data_returns_400(self):
        # set the mortgage_profile_uuid in the session
        url = reverse('mortgage_profiles:refinance_list')
        response = self.client.post(url, data={'kind': MortgageProfile.PURCHASE})
        self.assertEqual(response.status_code, 201)

        # start the test
        url = reverse('mortgage_profiles:rate_quote_service')
        response = self.client.get(url)
        expected = {'errors': {'is_enough_data': False, 'is_valid_state': False}}
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, expected)

    @with_httmock(mortech_response_success)
    def test_get_rate_quote_view_success(self):
        self.assertEqual(mortech_response_success.call, {'count': 0, 'called': False})
        url = reverse('mortgage_profiles:purchase_list')
        response = self.client.post(url, data={'kind': MortgageProfile.PURCHASE})
        self.assertEqual(response.status_code, 201)

        # acrobatics to create a mortgage profile with all the data
        uuid = self.client.session.get('mortgage_profile_uuid')
        self.assertIsNotNone(uuid)
        MortgageProfile.objects.get(uuid=uuid).delete()
        self.assertEqual(MortgageProfile.objects.count(), 0)
        MortgageProfilePurchaseFactory(uuid=uuid)

        # show that the response is 400 to start
        url = reverse('mortgage_profiles:rate_quote_service')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mortech_response_success.call, {'count': 1, 'called': True})
