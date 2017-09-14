# -*- coding: utf-8 -*-
from datetime import datetime
from decimal import Decimal
from pytz import UTC
from django.core.exceptions import ValidationError
from django.test import TestCase

from loans import factories
from loans import models
from mortgage_profiles.factories import MortgageProfilePurchaseFactory, MortgageProfileRefinanceFactory

# pylint: disable=protected-access


class TestLockOwnerAndTracker(TestCase):
    def test_default_is_advisor(self):
        self.assertEqual(models.LoanProfileV1().lock_owner, 'advisor')

    def test_invalid_choice_fails(self):
        loan_profile = factories.LoanProfileV1Factory(lock_owner='kubla')
        with self.assertRaises(ValidationError) as e:
            loan_profile.full_clean()
        msgs = [u"Value 'kubla' is not a valid choice."]
        self.assertEqual(e.exception.error_dict['lock_owner'][0].messages, msgs)

    def test_lock_owner_updated_updates(self):
        lp = factories.LoanProfileV1Factory()
        now = datetime.utcnow().replace(tzinfo=UTC)
        self.assertIsNone(lp.lock_owner_updated)
        lp.lock_owner = models.LoanProfileV1.LOCK_OWNER_CHOICES.customer
        lp.save()
        self.assertGreater(lp.lock_owner_updated, now)
        self.assertEqual(lp.lock_owner, 'customer')


class TestCheckPurchasePrice(TestCase):
    def test_check_purchase_price_all_set_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            down_payment_amount='124939',
            new_property_info_contract_purchase_price='300000')
        self.assertIsNone(lp._check_purchase_price())

    def test_check_purchase_price_no_down_payment_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            down_payment_amount=None,
            new_property_info_contract_purchase_price=None)
        self.assertIsNone(lp._check_purchase_price())

    def test_check_purchase_price_no_purchase_price_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            down_payment_amount='124939',
            new_property_info_contract_purchase_price=None)
        self.assertEqual(lp._check_purchase_price(),
                         'Down payment amount requires a purchase price')

    def test_check_purchase_price_zero_purchase_price_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            down_payment_amount='124939',
            new_property_info_contract_purchase_price=0)
        self.assertEqual(lp._check_purchase_price(),
                         'Down payment amount requires a purchase price')


class TestCheckSubjectProperty(TestCase):
    # Purchase
    def test_check_subject_property_purchase_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            new_property_address=factories.AddressV1Factory(
                city='',
                state='MI',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='',
                    state='',
                    postal_code='')])
        self.assertIsNone(lp._check_subject_property())

    def test_check_subject_property_purchase_no_property_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            new_property_address=None)
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertEqual(
            lp._check_subject_property(),
            'Subject property is not set')

    def test_check_subject_property_purchase_no_city_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            new_property_address=factories.AddressV1Factory(
                city='',
                state='Ann Arbor',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertIsNone(lp._check_subject_property())

    def test_check_subject_property_purchase_no_state_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            new_property_address=factories.AddressV1Factory(
                city='Ann Arbor',
                state='',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertEqual(
            lp._check_subject_property(),
            'Subject property state is not set')

    def test_check_subject_property_purchase_no_zip_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            new_property_address=factories.AddressV1Factory(
                city='',
                state='MI',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertIsNone(lp._check_subject_property())

    # Refinance -- Current
    def test_check_subject_property_refinance_current_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=True,
            new_property_address=factories.AddressV1Factory(
                city='',
                state='',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='',
                    state='MI',
                    postal_code='')])
        self.assertIsNone(lp._check_subject_property())

    def test_check_subject_property_refinance_current_no_property_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=True,
            new_property_address=factories.AddressV1Factory(
                city='Carmel',
                state='IN',
                postal_code='46032'))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[])
        self.assertEqual(
            lp._check_subject_property(),
            'Subject property is not set')

    def test_check_subject_property_refinance_current_no_city_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=True,
            new_property_address=factories.AddressV1Factory(
                city='Carmel',
                state='',
                postal_code='46032'))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='',
                    state='MI',
                    postal_code='')])
        self.assertIsNone(lp._check_subject_property())

    def test_check_subject_property_refinance_current_no_state_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=True,
            new_property_address=factories.AddressV1Factory(
                city='Carmel',
                state='IN',
                postal_code='46032'))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='',
                    state='',
                    postal_code='')])
        self.assertEqual(
            lp._check_subject_property(),
            'Subject property state is not set')

    def test_check_subject_property_refinance_current_no_zip_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=True,
            new_property_address=factories.AddressV1Factory(
                city='Carmel',
                state='IN',
                postal_code='46032'))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='',
                    state='MI',
                    postal_code='')])
        self.assertIsNone(lp._check_subject_property())

    # Refinance -- Other
    def test_check_subject_property_refinance_other_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=False,
            new_property_address=factories.AddressV1Factory(
                city='',
                state='MI',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[])
        self.assertIsNone(lp._check_subject_property())

    def test_check_subject_property_refinance_factory_pass(self):
        lp = factories.RefinanceOtherLoanProfileFactory()
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[])
        self.assertIsNone(lp._check_subject_property())

    def test_check_subject_property_refinance_other_no_property_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=False,
            new_property_address=None)
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertEqual(
            lp._check_subject_property(),
            'Subject property is not set')

    def test_check_subject_property_refinance_other_no_city_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=False,
            new_property_address=factories.AddressV1Factory(
                city='',
                state='MI',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertIsNone(lp._check_subject_property())

    def test_check_subject_property_refinance_other_no_state_fail(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=False,
            new_property_address=factories.AddressV1Factory(
                city='Ann Arbor',
                state='',
                postal_code='48103'))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertEqual(
            lp._check_subject_property(),
            'Subject property state is not set')

    def test_check_subject_property_refinance_other_no_zip_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=False,
            new_property_address=factories.AddressV1Factory(
                city='',
                state='MI',
                postal_code=''))
        factories.BorrowerV1Factory(
            loan_profile=lp,
            previous_addresses=[
                factories.AddressV1Factory(
                    city='Carmel',
                    state='IN',
                    postal_code='46032')])
        self.assertIsNone(lp._check_subject_property())


class TestCanSyncToEncompass(TestCase):
    def test_can_sync_to_encompass_purchase_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            down_payment_amount='124939',
            new_property_info_contract_purchase_price='300000',
            new_property_address=factories.AddressV1Factory(
                city='Ann Arbor',
                state='MI',
                postal_code='48103'))
        self.assertTrue(lp.can_sync_to_encompass())

    def test_can_sync_to_encompass_purchase_factory_pass(self):
        lp = factories.PurchaseLoanProfileFactory()
        self.assertTrue(lp.can_sync_to_encompass())

    def test_can_sync_to_encompass_refinance_pass(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            purpose_of_refinance='rate_or_term',
            is_refinancing_current_address=False,
            new_property_address=factories.AddressV1Factory(
                city='Ann Arbor',
                state='MI',
                postal_code='48103'))
        self.assertTrue(lp.subject_property_address)
        self.assertTrue(lp.can_sync_to_encompass())

    def test_can_sync_to_encompass_refinance_other_factory_pass(self):
        lp = factories.RefinanceOtherLoanProfileFactory()
        self.assertTrue(lp.can_sync_to_encompass())

    def test_can_sync_to_encompass_refinance_fail_no_purpose(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='refinance',
            is_refinancing_current_address=False,
            new_property_address=factories.AddressV1Factory(
                city='Ann Arbor',
                state='MI',
                postal_code='48103'))
        self.assertFalse(lp.can_sync_to_encompass())
        with self.assertRaisesMessage(Exception,
                                      'Refinance purpose is not set'):
            lp.can_sync_to_encompass(exception_cls=Exception)

    def test_can_sync_to_encompass_fail_no_purchase_price(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            down_payment_amount='124939',
            new_property_info_contract_purchase_price=None)
        self.assertFalse(lp.can_sync_to_encompass())
        with self.assertRaisesMessage(Exception,
                                      'Down payment amount requires a purchase price'):
            lp.can_sync_to_encompass(exception_cls=Exception)

    def test_can_sync_to_encompass_fail_no_property_address(self):
        lp = factories.LoanProfileV1Factory(
            purpose_of_loan='purchase',
            down_payment_amount='124939',
            new_property_info_contract_purchase_price='300000',
            new_property_address=factories.AddressV1Factory(
                city='Ann Arbor',
                state='',
                postal_code='48103'))
        self.assertFalse(lp.can_sync_to_encompass())
        with self.assertRaisesMessage(Exception, 'Subject property state is not set'):
            lp.can_sync_to_encompass(exception_cls=Exception)


class TestUpdateFromMortgageProfile(TestCase):
    maxDiff = None

    def test_no_mortgage_profile_returns_no_updated_fields(self):
        lp = factories.LoanProfileV1Factory()
        updated_fields = lp.update_from_mortgage_profile()
        self.assertEqual(updated_fields, [])

    def test_purchase_mp_updates(self):
        lp_before = {
            'purpose_of_loan': 'refinance',
            'property_purpose': 'secondary_residence',
            'base_loan_amount': None,
            'property_value_estimated': None,
            'down_payment_amount': None,
            'new_property_info_contract_purchase_price': None,
        }
        lp_after = {
            'purpose_of_loan': u'purchase',
            'property_purpose': u'',
            'base_loan_amount': Decimal('600000'),
            'property_value_estimated': Decimal('1000000'),
            'down_payment_amount': Decimal('400000'),
            'new_property_info_contract_purchase_price': Decimal('1000000'),
        }
        # check values before update
        lp = factories.LoanProfileV1Factory(**lp_before)
        expected = {}
        for field, value in lp_before.iteritems():
            expected.update({field: getattr(lp, field)})
        self.assertEqual(lp_before, expected)

        # create mp
        mp = MortgageProfilePurchaseFactory(loan_profilev1=lp)

        # check value after update
        updated_fields = lp.update_from_mortgage_profile()
        expected = {}
        for field, value in lp_after.iteritems():
            expected.update({field: getattr(lp, field)})
        self.assertEqual(lp_after, expected)
        self.assertItemsEqual(updated_fields, lp_after.keys())

    def test_refi_mp_updates(self):
        lp_before = {
            'purpose_of_loan': 'purchase',
            'property_purpose': '',
            'base_loan_amount': None,
            'property_value_estimated': None,
            'is_cash_out': None,
            'purpose_of_refinance': None,
            'refinance_amount_of_existing_liens': None,
        }
        lp_after = {
            'purpose_of_loan': u'refinance',
            'property_purpose': u'primary_residence',
            'base_loan_amount': Decimal('600000'),
            'property_value_estimated': Decimal('1000000'),
            'is_cash_out': False,
            'purpose_of_refinance': 'rate_or_term',
            'refinance_amount_of_existing_liens': Decimal('600000'),
        }
        # check values before update
        lp = factories.LoanProfileV1Factory(**lp_before)
        expected = {}
        for field, value in lp_before.iteritems():
            expected.update({field: getattr(lp, field)})
        self.assertEqual(lp_before, expected)

        # create mp
        mp_fields = {

        }
        mp = MortgageProfileRefinanceFactory(
            loan_profilev1=lp,
            purpose='lower_mortgage_payments',
            property_occupation='my_current_residence',
            mortgage_owe=600000,
            property_value=1000000)

        # check value after update
        updated_fields = lp.update_from_mortgage_profile()
        expected = {}
        for field, value in lp_after.iteritems():
            expected.update({field: getattr(lp, field)})
        self.assertEqual(lp_after, expected)
        self.assertItemsEqual(updated_fields, lp_after.keys())
