from mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError

from rest_framework import serializers

from accounts import factories
from accounts import models
from loans import factories as loan_factories


class CustomerModelTests(TestCase):
    def test_default_contact_passes_validation_and_sets_correct_defaults(self):
        customer = factories.CustomerFactory()
        self.assertIsNone(customer.full_clean())
        self.assertEqual(customer.contact_preferences, {'phone_ok': True, 'email_ok': True, 'text_ok': False})
        self.assertEqual(customer.has_opted_out_of_email, False)

    def test_contact_preferences_cannot_be_empty_obj(self):
        customer = factories.CustomerFactory(contact_preferences={})
        try:
            customer.full_clean()
            self.assertFail()
        except ValidationError as e:
            self.assertEqual(e.messages, [u'This field cannot be blank.'])

    def test_invalid_contact_preferences_raises_errors(self):
        customer = factories.CustomerFactory(contact_preferences={
            'phone': False,
            'text_ok': 'hello',
            'invalid_entry': '',
        })
        error_msgs = [u"u'phone_ok' is a required property",
                      u"u'email_ok' is a required property",
                      u"'hello' is not of type u'boolean'"]
        possible_a = [u"Additional properties are not allowed ('phone', 'invalid_entry' were unexpected)",
                      u"Additional properties are not allowed ('invalid_entry', 'phone' were unexpected)"]
        try:
            customer.full_clean()
            self.assertFail()
        except ValidationError as e:
            for item in e.messages:
                if item not in error_msgs:
                    self.assertIn(item, possible_a)
            self.assertIn(u"u'phone_ok' is a required property", e.messages)
            self.assertIn(u"u'email_ok' is a required property", e.messages)
            self.assertIn(u"'hello' is not of type u'boolean'", e.messages)


class CustomerDuplicateEmailTest(TestCase):
    @patch('accounts.models.logger')
    def test_duplicate_email_usernames_returns_true(self, mock_logger):
        c1 = factories.CustomerFactory(email='rex.Salisbury@example.com')
        factories.CustomerFactory(email='Rex.salisbury@example.com')
        result = c1.check_for_duplicate_email(log_info=True)
        self.assertTrue(result)
        self.assertTrue(mock_logger.info.called)

    @patch('accounts.models.logger')
    def test_duplicate_email_usernames_returns_true_and_log_toggle_works(self, mock_logger):
        c1 = factories.CustomerFactory(email='rex.Salisbury@example.com')
        factories.CustomerFactory(email='Rex.salisbury@example.com')
        result = c1.check_for_duplicate_email(log_info=False)
        self.assertTrue(result)
        self.assertFalse(mock_logger.info.called)

    @patch('accounts.models.logger')
    def test_no_duplicate_email_usernames_returns_false(self, mock_logger):
        c1 = factories.CustomerFactory(email='rex.Salisbury@example.com')
        result = c1.check_for_duplicate_email(log_info=True)
        self.assertFalse(result)
        self.assertFalse(mock_logger.info.called)


class CustomerCurrentLoanProfileTests(TestCase):
    def test_no_loan_profile_returns_none(self):
        customer = factories.CustomerFactory()
        self.assertIsNone(customer.current_loan_profile)

    def test_respects_is_active_flag(self):
        customer = factories.CustomerFactory()
        loan_factories.LoanProfileV1Factory(customer=customer, is_active=False)
        self.assertIsNone(customer.current_loan_profile)

    def test_returns_most_recent(self):
        customer = factories.CustomerFactory()
        loan_factories.LoanProfileV1Factory(customer=customer)
        lp_2 = loan_factories.LoanProfileV1Factory(customer=customer)
        self.assertEqual(customer.current_loan_profile.id, lp_2.id)


class FetchUserOrRaiseErrorTests(TestCase):
    def test_returns_user_if_exists(self):
        customer = factories.CustomerFactory()
        user, created = models.Customer.objects.fetch_user_or_raise_error(customer.email)
        self.assertEqual(user, customer)
        self.assertFalse(created)

    def test_creates_user_if_does_not_exist(self):
        user, created = models.Customer.objects.fetch_user_or_raise_error(
            'test@example.com', data={'first_name': 'chip'})
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'chip')
        self.assertTrue(created)

    def test_raises_error_if_user_exists_but_is_of_wrong_type(self):
        advisor = factories.AdvisorFactory()
        with self.assertRaises(serializers.ValidationError) as e:
            models.Customer.objects.fetch_user_or_raise_error(advisor.email)
        self.assertEqual(e.exception.detail, {'errors': ['email already exists for a different type of user']})
