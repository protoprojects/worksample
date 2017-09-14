from django.test import TestCase

from mock import patch

from contacts import serializers, models
from core.models import Recaptcha
from pages.factories import StateLicenseFactory


class ContactRequestUnlicensedStateTests(TestCase):
    # pylint: disable=no-self-use
    def setUp(self):
        recaptcha = Recaptcha.get_solo()
        recaptcha.enable = False
        recaptcha.save()

    def test_certain_fields_are_required(self):
        expected = {
            'unlicensed_state_code': [u'This field is required.'],
            'first_name': [u'This field is required.'],
            'last_name': [u'This field is required.'],
            'email': [u'This field is required.'],
        }
        serializer = serializers.ContactRequestUnlicensedStateSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, expected)

    def test_certain_fields_cannot_be_null(self):
        data = {
            'unlicensed_state_code': None,
            'first_name': None,
            'last_name': None,
            'phone': None,  # this can be none
            'email': None,
        }
        expected = {
            'unlicensed_state_code': [u'This field may not be null.'],
            'first_name': [u'This field may not be null.'],
            'last_name': [u'This field may not be null.'],
            'email': [u'This field may not be blank.'],
        }
        serializer = serializers.ContactRequestUnlicensedStateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, expected)

    def test_creates_new_instance(self):
        data = {
            'unlicensed_state_code': 'California',
            'first_name': 'Ymir',
            'last_name': 'Icegiant',
            'email': 'test@example.com',
            'phone': '301 999 0232',
        }
        cr = models.ContactRequestUnlicensedState.objects.create(**data)
        serializer = serializers.ContactRequestUnlicensedStateSerializer(cr)
        self.assertEqual(serializer.data, data)
        self.assertIsInstance(serializer.instance, models.ContactRequestUnlicensedState)

    # pylint: disable=no-self-use
    @patch('contacts.serializers.logger')
    def test_logs_error_when_a_contact_request_is_made_for_a_state_we_are_licensed_in(self, mock_logger):
        StateLicenseFactory(state_name='California')
        data = {'unlicensed_state_code': 'CA'}
        serializer = serializers.ContactRequestUnlicensedStateSerializer(data=data)
        serializer.is_valid()
        mock_logger.error.assert_called_with(
            'CONTACT-REQUEST-UNLICENSED-STATE-FOR-STATE-WITH-LICENSE unlicensed_state_code %s', 'CA')
