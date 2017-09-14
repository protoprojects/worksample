import logging

from twilio import twiml

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.http import urlencode

from rest_framework import status

from accounts import factories
from accounts.models import Customer
from accounts.tests.helpers import JWTAuthAPITestCase
from accounts.views import PhoneVerificationTwilioCallback
from core.utils import LogMutingTestMixinBase


class AccountsTest(JWTAuthAPITestCase):

    def setUp(self):
        self.user = Customer(email='sample@sample.com')
        self.user.save()
        super(AccountsTest, self).setUp()

    def test_create_user_valid(self):
        """
        Ensure we can create a new account.

        """
        url = reverse('encompass_users:user')

        data = {
            'email': 'foo@bar.com',
            'phone': '+1-234-5678-900'
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=self.get_jwt_auth())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('id'))

        for key, value in data.iteritems():
            self.assertEqual(value, response.data.get(key))

        user = Customer.objects.get(id=response.data.get('id'))
        self.assertIsNotNone(user.password)

    def test_create_user_invalid(self):
        """
        Ensure we cannot create a new account without an email.

        """
        url = reverse('encompass_users:user')

        data = {
            'phone': '+1-234-5678-900'
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=self.get_jwt_auth())

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestPhoneVerificationTwilioCallback(TestCase):
    def setUp(self):
        self.phv = factories.PhoneVerificationFactory()
        self.url = reverse('accounts:api-phone-verification-twilio-callback')

    def test_view_permissions(self):
        permission_classes = [perm.__name__ for perm in PhoneVerificationTwilioCallback.permission_classes]
        self.assertEqual(permission_classes, ['TwilioCallbackPermission'])

    def test_successful_response(self):
        r = twiml.Response()
        r.say('Your verification code is')
        PhoneVerificationTwilioCallback._say_code(r, self.phv.code)
        r.pause(length=2)  # wait 2 seconds before repeat
        r.say('Repeat again')
        PhoneVerificationTwilioCallback._say_code(r, self.phv.code)
        url = self.url + '?' + urlencode({'verification_code': self.phv.code})
        response = self.client.post(url, data=urlencode({'AccountSid': settings.TWILIO_ACCOUNT_SID}),
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(r.toxml(), response.content)

    def test_unsuccessful_response(self):
        url = self.url + '?' + urlencode({'verification_code': self.phv.code})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {"detail": "Authentication credentials were not provided."})


class CustomerEmailVerificationFailMixin(object):
    def setUp(self):
        super(CustomerEmailVerificationFailMixin, self).setUp()
        self.cev = factories.CustomerEmailValidationFactory()
        self.assertEqual(self.cev.is_redeemed, False)
        self.assertEqual(self.cev.is_active, True)

        self.customer = factories.CustomerFactory(email_validation=self.cev)
        self.assertEqual(self.customer.is_active, True)

    def test_code_does_not_exist(self):
        url = self.url + '?' + urlencode({'code': 'fake_code'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Code doesn\'t exist.'})

    def test_code_has_been_deactivated(self):
        self.cev.is_active = False
        self.cev.save()
        url = self.url + '?' + urlencode({'code': self.cev.code})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data, {'detail': 'Code has been deactivated.'})

    def test_already_verified(self):
        self.cev.is_redeemed = True
        self.cev.save()
        url = self.url + '?' + urlencode({'code': self.cev.code})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'detail': 'Code has already been verified.'})


class TestVerifyEmailCustomerView(CustomerEmailVerificationFailMixin, LogMutingTestMixinBase, TestCase):
    log_names = ['sample.accounts.views']
    mute_level = logging.ERROR
    url = reverse('accounts:api-verify-email')

    def test_code_successfully_verified(self):
        url = self.url + '?' + urlencode({'code': self.cev.code})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'detail': 'Code successfully verified.'})


class TestDeclineEmailCustomerView(CustomerEmailVerificationFailMixin, LogMutingTestMixinBase, TestCase):
    log_names = ['sample.accounts.views']
    mute_level = logging.ERROR
    url = reverse('accounts:api-decline-email')

    def test_code_successfully_repudiated(self):
        url = self.url + '?' + urlencode({'code': self.cev.code})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'detail': 'Code successfully repudiated.'})
        self.customer.refresh_from_db()
        self.cev.refresh_from_db()
        self.assertEqual(self.customer.is_active, False)
        self.assertEqual(self.cev.is_redeemed, False)
        self.assertEqual(self.cev.is_active, False)

