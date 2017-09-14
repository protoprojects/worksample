import logging
import mock

from django.core.urlresolvers import reverse
from django.test import TestCase

from rest_framework.test import APITestCase

from contacts import models, factories
from contacts.api_views import NotificationMixin, LocationCountyLookup, Location
from core.tests import CeleryTaskTestCase
from core.models import Recaptcha
from mortgage_profiles.factories import MortgageProfilePurchaseFactory, RateQuoteLenderFactory


logger = logging.getLogger("sample.contacts.test_api_views")


class ContactRequestViewTestMixin(object):
    # pylint: disable=no-self-use
    def setUp(self):
        recaptcha = Recaptcha.get_solo()
        recaptcha.enable = False
        recaptcha.save()

    API_ENDPOINT = None
    MODEL = None

    DATA = {
        'firstName': 'Test',
        'lastName': 'Test',
        'phone': '5555555555',
        'email': 'anonymous@example.com',
    }

    def test_create(self):
        self.assertFalse(self.MODEL.objects.filter(email=self.DATA['email']).exists())
        response = self.client.post(self.API_ENDPOINT, data=self.DATA)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(self.MODEL.objects.filter(email=self.DATA['email']).exists())

    @mock.patch('vendors.tasks.SalesforcePush.push')
    def test_salesforce_lead_sent(self, mock_saleforce_push):
        response = self.client.post(self.API_ENDPOINT, data=self.DATA)
        logger.debug('SF-LEAD-PATCHED-PUSH url: %s: %s', self.API_ENDPOINT, response)
        self.assertTrue(self.MODEL.objects.filter(email=self.DATA['email']).exists())
        mock_saleforce_push.assert_called_once()

    @mock.patch('contacts.api_views.NotificationMixin.send_administrative_notification')
    @mock.patch('vendors.tasks.SalesforcePush.push')
    def test_notifications_was_sent(self, mock_admin_send, mock_salesforce_push):
        self.client.post(self.API_ENDPOINT, data=self.DATA)
        self.assertTrue(self.MODEL.objects.filter(email=self.DATA['email']).exists())
        mock_admin_send.assert_called_once()
        mock_salesforce_push.assert_called_once()


class TestContactRequestMortgageProfileView(ContactRequestViewTestMixin, CeleryTaskTestCase, APITestCase):
    API_ENDPOINT = reverse('contact_requests:mortgage_profile_list')
    MODEL = models.ContactRequestMortgageProfile

    def _create_mp(self):
        url = reverse('mortgage_profiles:purchase_list')
        data = {
            'kind': 'purchase',
            'purchase_timing': 'researching_options',
            'property_occupation': 'first_time_homebuyer',
            'property_type': 'single_family'
        }
        return self.client.post(url, data, format='json').data

    def test_create(self):
        self._create_mp()

        self.assertIsNotNone(self.client.session.get('mortgage_profile_uuid'))
        self.assertFalse(self.MODEL.objects.filter(email=self.DATA['email']).exists())

        response = self.client.post(self.API_ENDPOINT, data=self.DATA)
        self.assertEqual(response.status_code, 201)
        crmps = self.MODEL.objects.filter(email=self.DATA['email'])
        self.assertTrue(crmps.exists)
        self.assertEqual(crmps.count(), 1)
        crmp = crmps[0]
        self.assertIsNotNone(crmp.mortgage_profile)
        self.assertIsNone(self.client.session.get('mortgage_profile_uuid'))


class TestContactRequestMobileProfileView(
        ContactRequestViewTestMixin, CeleryTaskTestCase, APITestCase):
    API_ENDPOINT = reverse('contact_requests:contact_request_mobile_profile')
    MODEL = models.ContactRequestMobileProfile

    @mock.patch('vendors.tasks.SalesforcePush.push')
    def test_create(self, mock_saleforce_push):
        super(TestContactRequestMobileProfileView, self).test_create()
        mock_saleforce_push.assert_called_once()


class TestContactRequestConsultationView(
        ContactRequestViewTestMixin, CeleryTaskTestCase, APITestCase):
    API_ENDPOINT = reverse('contact_requests:contact_request_consultation')
    MODEL = models.ConsultationRequest

    def __init__(self, *args, **kwargs):
        super(TestContactRequestConsultationView, self).__init__(*args, **kwargs)
        self.DATA.update({'mortgageTiming': 'immediate'})


class TestContactRequestAboutUsView(
        ContactRequestViewTestMixin, CeleryTaskTestCase, APITestCase):
    API_ENDPOINT = reverse('contact_requests:contact_request_about_us')
    MODEL = models.ContactRequestAboutUs

    def __init__(self, *args, **kwargs):
        super(TestContactRequestAboutUsView, self).__init__(*args, **kwargs)
        self.DATA.update({'message': 'test message'})


class TestContactRequestUnlicensedStateView(APITestCase):
    # pylint: disable=no-self-use
    def setUp(self):
        recaptcha = Recaptcha.get_solo()
        recaptcha.enable = False
        recaptcha.save()

    def test_create(self):
        data = {
            'firstName': 'Test',
            'lastName': 'Test',
            'phone': '5555555555',
            'email': 'anonymous@example.com',
            'unlicensed_state_code': 'CA',
        }
        url = reverse('contact_requests:contact_request_unlicensed_state_list')
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(models.ContactRequestUnlicensedState.objects.filter(email=data['email']).exists())

    def test_failure(self):
        expected = {
            'unlicensed_state_code': [u'This field is required.'],
            'first_name': [u'This field is required.'],
            'last_name': [u'This field is required.'],
            'email': [u'This field is required.'],
        }
        url = reverse('contact_requests:contact_request_unlicensed_state_list')
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, expected)


class TestContactRequestPartnerView(
        ContactRequestViewTestMixin, CeleryTaskTestCase, APITestCase):
    API_ENDPOINT = reverse('contact_requests:contact_request_partner')
    MODEL = models.ContactRequestPartner


class TestContactRequestLandingView(
        ContactRequestViewTestMixin, CeleryTaskTestCase, APITestCase):
    API_ENDPOINT = reverse('contact_requests:contact_request_landing')
    MODEL = models.ContactRequestLanding

    def __init__(self, *args, **kwargs):
        super(TestContactRequestLandingView, self).__init__(*args, **kwargs)
        self.DATA.update({'mortgageTiming': 'immediate'})


class TestContactRequestLandingExtendedView(
        ContactRequestViewTestMixin, CeleryTaskTestCase, APITestCase):
    API_ENDPOINT = reverse('contact_requests:contact_request_landing_extended')
    MODEL = models.ContactRequestLandingExtended

    def __init__(self, *args, **kwargs):
        super(TestContactRequestLandingExtendedView, self).__init__(*args, **kwargs)
        self.DATA.update({
            'propertyZipcode': '11111',
            'propertyState': 'CA',
            'propertyCounty': 'San Francisco County',
            'ownershipTime': 'Not Sure',
            'mortgageProfileKind': 'purchase',
            'creditRating': 'Good (720-739)',
            'purchasePropertyValue': '999999',
            'purchaseDownPayment': '199999'})


class TestNotification(TestCase):
    @mock.patch('contacts.api_views.notification.send')
    def test_send_administrative_notification(self, mocked_notification):
        contact_request = factories.ContactRequestMortgageProfileFactory()
        lender = RateQuoteLenderFactory()
        mortgage_profile = MortgageProfilePurchaseFactory()

        cls = NotificationMixin()
        cls.request = mock.MagicMock(
            data={
                'mortgage_profile_id': mortgage_profile.uuid,
                'lender_id': lender.id,
            }
        )
        cls.object = contact_request
        cls.ADMINISTRATIVE_NOTIFICATION_TYPE = 'administrative_contact_request'

        cls.send_administrative_notification()
        self.assertTrue(mocked_notification.called)

        called_args = mocked_notification.call_args[0]
        self.assertTrue(isinstance(called_args[0][0], mock.MagicMock))
        self.assertEqual(called_args[1], cls.ADMINISTRATIVE_NOTIFICATION_TYPE)

        self.assertEqual(called_args[2]['lead_type'], contact_request.get_kind_display())
        self.assertEqual(called_args[2]['contact_request'], contact_request)
        self.assertEqual(called_args[2]['mortgage_profile'], mortgage_profile)
        self.assertEqual(called_args[2]['lender'], lender)
        self.assertEqual(called_args[2]['lender_calculations'].instance, mortgage_profile)
        self.assertEqual(called_args[2]['lender_calculations'].lender, lender)


class TestLocationCountyLookup(TestCase):
    def setUp(self):
        from cacheops import invalidate_model
        invalidate_model(Location)
        super(TestLocationCountyLookup, self).setUp()

    def test_get_empty_queryset(self):
        cls = LocationCountyLookup()
        cls.request = mock.MagicMock(query_params={})
        qs = cls.get_queryset()
        self.assertEqual(list(qs), [])

    def test_get_non_empty_queryset(self):
        cls = LocationCountyLookup()
        cls.request = mock.MagicMock(query_params={'state': 'CA'})
        qs = cls.get_queryset()
        self.assertEqual(list(qs), list(Location.objects.filter(state='CA')))

    def test_get_result(self):
        Location.objects.create(state='XX', county='AAA')
        Location.objects.create(state='XX', county='BBB')
        Location.objects.create(state='XX', county='CCC')

        Location.objects.create(state='CA', county='EEE')
        Location.objects.create(state='NY', county='NY')

        url = reverse('contact_requests:location_county_lookup')
        response = self.client.get('%s?state=XX' % url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data, ['AAA', 'BBB', 'CCC'])
