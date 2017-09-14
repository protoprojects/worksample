# -*- coding: utf-8 -*-
import datetime
from copy import copy
from dateutil.relativedelta import relativedelta

from django.core.exceptions import ValidationError
from django.db.utils import DataError
from django.test import TestCase

from loans import factories
from loans.models import DemographicsV1, LoanProfileV1
from mortgage_profiles.factories import MortgageProfileRefinanceFactory
from mortgage_profiles.models import MortgageProfileRefinance


AP = 'advisor_portal'
CP = 'customer_portal'


class BorrowerTestMixin(object):
    def test_address_property_returns_correct_object(self):
        address1 = factories.AddressV1Factory(
            start_date=datetime.date(year=2014, month=1, day=1),
            end_date=datetime.date(year=2015, month=1, day=1),
        )
        address2 = factories.AddressV1Factory(
            start_date=datetime.date(year=1995, month=1, day=1),
            end_date=datetime.date(year=2005, month=1, day=1),
        )
        address3 = factories.AddressV1Factory(
            start_date=datetime.date(year=2005, month=1, day=1),
            end_date=datetime.date(year=2014, month=1, day=1),
        )
        self.borrower.previous_addresses.add(address1, address2, address3)
        self.borrower.save()
        self.assertEqual(self.borrower.address, address1)

    def test_employment_property_returns_correct_object(self):
        employment1 = factories.EmploymentV1Factory(
            start_date=datetime.date(year=1995, month=1, day=1),
            end_date=datetime.date(year=2005, month=1, day=1),
        )
        employment2 = factories.EmploymentV1Factory(
            start_date=datetime.date(year=2014, month=1, day=1),
            end_date=datetime.date(year=2015, month=1, day=1),
        )
        employment3 = factories.EmploymentV1Factory(
            start_date=datetime.date(year=2005, month=1, day=1),
            end_date=datetime.date(year=2014, month=1, day=1),
        )
        self.borrower.previous_employment.add(employment1, employment2, employment3)
        self.borrower.save()
        self.assertEqual(self.borrower.employment, employment2)


class TestBorrowerV1(TestCase, BorrowerTestMixin):
    def setUp(self):
        self.borrower = factories.BorrowerV1Factory(
            loan_profile=factories.LoanProfileV1Factory()
        )


class TestCoborrowerV1(TestCase, BorrowerTestMixin):
    def setUp(self):
        self.borrower = factories.CoborrowerV1Factory(
            borrower=factories.BorrowerV1Factory(
                loan_profile=factories.LoanProfileV1Factory()
            )
        )


class TestMismoDemographicsV1Properties(TestCase):
    def test_when_mismo_properties_return_not_provided(self):
        loan_profile = factories.LoanProfileV1Factory(
            application_taken_method=LoanProfileV1.APPLICATION_TAKEN_METHOD_CHOICES.telephone)
        demographics = factories.DemographicsV1Factory(
            are_ethnicity_questions_skipped=True)
        factories.BorrowerV1Factory(
            loan_profile=loan_profile,
            demographics=demographics)
        self.assertEqual(demographics.mismo_races, [DemographicsV1.NOT_PROVIDED])
        self.assertEqual(demographics.mismo_ethnicity, DemographicsV1.NOT_PROVIDED)
        self.assertEqual(demographics.mismo_gender, 'InformationNotProvidedUnknown')

    def test_mismo_properties_map_values(self):
        loan_profile = factories.LoanProfileV1Factory(
            application_taken_method=LoanProfileV1.APPLICATION_TAKEN_METHOD_CHOICES.face_to_face)
        demographics = factories.DemographicsV1Factory(
            are_ethnicity_questions_skipped=False,
            ethnicity='hispanic_or_latino',
            race=['Asian'],
            gender='female')
        factories.BorrowerV1Factory(
            loan_profile=loan_profile,
            demographics=demographics)
        self.assertEqual(demographics.mismo_ethnicity, 'HispanicOrLatino')
        self.assertEqual(demographics.mismo_races, ['Asian'])
        self.assertEqual(demographics.mismo_gender, 'Female')


class TestAddressYearsMonthsSetter(TestCase):
    def test_setter_works(self):
        address = factories.AddressV1Factory(years=1, months=2)
        self.assertEqual(address.years, 1)
        self.assertEqual(address.months, 2)
        address.years, address.months = 4, 3
        self.assertEqual(address.years, 4)
        self.assertEqual(address.months, 3)

        self.assertEqual(address.end_date.date(), datetime.datetime.today().date())
        start_date = address.end_date - relativedelta(years=4, months=3)
        self.assertEqual(address.start_date.date(), start_date.date())


class TestRespaTriggered(TestCase):
    def test_defaults(self):
        loan_profile = factories.LoanProfileV1Factory()
        self.assertEqual(loan_profile.respa_triggered, False)
        self.assertEqual(loan_profile.respa_triggered_at, None)

    def test_setting_to_false_raises_exception(self):
        loan_profile = factories.LoanProfileV1Factory()
        with self.assertRaisesMessage(AttributeError, "can't set attribute"):
            loan_profile.respa_triggered = False

    def test_trigger_respa_sets_timestamp(self):
        loan_profile = factories.LoanProfileV1Factory()
        loan_profile.trigger_respa()
        self.assertEqual(loan_profile.respa_triggered, True)
        self.assertIsInstance(loan_profile.respa_triggered_at, datetime.datetime)

    def test_trigger_respa_second_time_does_not_change_timestampe(self):
        loan_profile = factories.LoanProfileV1Factory()
        # set it to true the first time
        loan_profile.trigger_respa()
        first_update = copy(loan_profile.respa_triggered_at)

        # set to true a second time
        loan_profile.trigger_respa()
        second_update = copy(loan_profile.respa_triggered_at)
        self.assertEqual(loan_profile.respa_triggered, True)
        self.assertEqual(first_update, second_update)


class TestTriggerRespaForConsumer(TestCase):
    def assertCriteriaAreCorrect(self, loan_profile, criteria, can_trigger, criteria_for=CP, did_trigger=None):
        if did_trigger is None:
            did_trigger = can_trigger

        if criteria_for == CP:
            result = loan_profile.respa_criteria_for_consumer_portal()
        else:
            result = loan_profile.respa_criteria_for_advisor_portal()

        for key, value in criteria.items():
            self.assertIn(key, result)
            msg = 'Criterion: {}: {} != {}'.format(key, value, result[key])
            self.assertEqual(value, result[key], msg)

        if criteria_for == CP:
            self.assertEqual(loan_profile.can_trigger_respa_for_consumer_portal(), can_trigger)
            self.assertEqual(loan_profile.trigger_respa_for_consumer_portal(), did_trigger)
        else:
            self.assertEqual(loan_profile.can_trigger_respa_for_advisor_portal(), can_trigger)
            self.assertEqual(loan_profile.trigger_respa_for_advisor_portal(), did_trigger)


    def test_loan_profile_base_scenario(self):
        # to start RESPA cannot be triggered...
        loan_profile = factories.LoanProfileV1Factory(
            purpose_of_loan='',
            property_purpose='')
        criteria = {
            u'has_borrower_ssn': None,
            u'is_refinance': None,
            u'is_primary_residence': None}
        trigger = False
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)

    def test_loan_profile_borrower_ssn(self):
        '''Provide a borrower without and with SSN'''
        loan_profile = factories.LoanProfileV1Factory(
            purpose_of_loan='',
            property_purpose='')
        borrower = factories.BorrowerV1Factory(
            loan_profile=loan_profile,
            ssn='')
        criteria = {u'has_borrower_ssn': False}
        trigger = False
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)
        borrower.ssn = '666121234'
        borrower.save()
        criteria = {u'has_borrower_ssn': True}
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)

    def test_purpose_of_loan(self):
        loan_profile = factories.LoanProfileV1Factory(
            purpose_of_loan='',
            property_purpose='')
        MortgageProfileRefinanceFactory(loan_profilev1=loan_profile)
        criteria = {u'is_refinance': None}
        trigger = False
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)
        loan_profile.purpose_of_loan = loan_profile.PURPOSE_OF_LOAN.purchase
        loan_profile.save()
        criteria = {u'is_refinance': False}
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)
        loan_profile.purpose_of_loan = loan_profile.PURPOSE_OF_LOAN.refinance
        loan_profile.save()
        criteria = {u'is_refinance': True}
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)

    def test_property_purpose(self):
        # The borrower demographics and mortgage profile values are to ensure
        # the primary residence information is taken from the loan profile
        loan_profile = factories.LoanProfileV1Factory(
            purpose_of_loan='',
            property_purpose='')
        factories.BorrowerV1Factory(
            loan_profile=loan_profile,
            demographics=factories.DemographicsV1Factory(
                plans_to_occupy_as_primary_residence=True))
        MortgageProfileRefinanceFactory(
            loan_profilev1=loan_profile,
            property_occupation=MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES.primary)
        criteria = {u'is_primary_residence': None}
        trigger = False
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)
        for purpose in (
                loan_profile.sample_PROPERTY_PURPOSES.investor,
                loan_profile.sample_PROPERTY_PURPOSES.second_home):
            loan_profile.property_purpose = purpose
            loan_profile.save()
            criteria = {u'is_primary_residence': False}
            self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)
        loan_profile.property_purpose = loan_profile.sample_PROPERTY_PURPOSES.primary_residence
        loan_profile.save()
        criteria = {u'is_primary_residence': True}
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)

    def test_loan_profile_trigger_with_criteria_for_customer_portal(self):
        loan_profile = factories.LoanProfileV1Factory(
            purpose_of_loan='',
            property_purpose='')
        criteria = {
            u'has_borrower_ssn': None,
            u'is_refinance': None,
            u'is_primary_residence': None}
        trigger = False
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)
        loan_profile.purpose_of_loan = loan_profile.PURPOSE_OF_LOAN.refinance
        loan_profile.property_purpose = loan_profile.sample_PROPERTY_PURPOSES.primary_residence
        factories.BorrowerV1Factory(
            loan_profile=loan_profile,
            ssn='666121234')
        criteria = {
            u'has_borrower_ssn': True,
            u'is_refinance': True,
            u'is_primary_residence': True}
        trigger = True
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger)

    def test_loan_profile_trigger_with_criteria_for_advisor_portal(self):
        loan_profile = factories.LoanProfileV1Factory()
        criteria = {
            'has_property_value': True,
            'address_is_complete': False,
            'has_base_loan_amount': True,
            'has_borrower_ssn': False,
            'borrower_first_name_filled': False,
            'borrower_last_name_filled': False,
            'has_base_income': False
        }
        trigger = False
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger, criteria_for=AP)

        loan_profile = factories.PurchaseLoanProfileFactory()

        factories.BorrowerV1Factory(
            loan_profile=loan_profile,
            ssn='666121234',
            income=[
                factories.BaseIncomeFactory(value='123')
            ],
        )
        criteria = {
            'has_property_value': True,
            'address_is_complete': True,
            'has_base_loan_amount': True,
            'has_borrower_ssn': True,
            'borrower_first_name_filled': True,
            'borrower_last_name_filled': True,
            'has_base_income': True
        }
        trigger = True
        self.assertCriteriaAreCorrect(loan_profile, criteria, trigger, criteria_for=AP)


class TestLoanProfileSource(TestCase):
    def test_no_customer_is_advisor_portal(self):
        loan_profile = factories.LoanProfileV1Factory(customer=None)
        self.assertFalse(loan_profile.has_customer())
        self.assertEqual(loan_profile.source, 'advisor_portal')

    def test_customer_is_customer_portal(self):
        loan_profile = factories.LoanProfileV1Factory()
        self.assertTrue(loan_profile.has_customer())
        self.assertEqual(loan_profile.source, 'customer_portal')


class TestBorrowerPreviousResidences(TestCase):
    def test_residence_history_when_when_living_together_is_none(self):
        lp = factories.LoanProfileV1Factory()
        addr = factories.AddressV1Factory()
        bor = factories.BorrowerV1Factory(loan_profile=lp)
        bor.previous_addresses.add(addr)
        cob = factories.CoborrowerV1Factory(borrower=bor, living_together_two_years=None)
        self.assertEqual(bor.get_current_residence(), addr)
        self.assertEqual(cob.get_current_residence(), None)
        self.assertEqual(list(bor.get_previous_residences()), [addr])
        self.assertEqual(list(cob.get_previous_residences()), [])

    def test_residence_history_when_living_together_is_true(self):
        lp = factories.LoanProfileV1Factory()
        addr = factories.AddressV1Factory()
        bor = factories.BorrowerV1Factory(loan_profile=lp)
        bor.previous_addresses.add(addr)
        cob = factories.CoborrowerV1Factory(borrower=bor, living_together_two_years=True)
        self.assertEqual(bor.get_current_residence(), addr)
        self.assertEqual(cob.get_current_residence(), addr)
        self.assertEqual(list(bor.get_previous_residences()), [addr])
        self.assertEqual(list(cob.get_previous_residences()), [addr])

    def test_residence_history_when_living_together_is_false(self):
        lp = factories.LoanProfileV1Factory()
        addr_1 = factories.AddressV1Factory()
        addr_2 = factories.AddressV1Factory()
        bor = factories.BorrowerV1Factory(loan_profile=lp)
        bor.previous_addresses.add(addr_1)
        cob = factories.CoborrowerV1Factory(borrower=bor, living_together_two_years=False)
        cob.previous_addresses.add(addr_2)
        self.assertEqual(bor.get_current_residence(), addr_1)
        self.assertEqual(cob.get_current_residence(), addr_2)
        self.assertEqual(list(bor.get_previous_residences()), [addr_1])
        self.assertEqual(list(cob.get_previous_residences()), [addr_2])

        # test what happens when updated to true
        cob.living_together_two_years = True
        self.assertEqual(cob.get_current_residence(), addr_1)
        self.assertEqual(list(cob.get_previous_residences()), [addr_1])


class TestYearsOfResidenceHistory(TestCase):
    def test_with_start_and_end_date(self):
        addr = factories.AddressV1Factory(start_date=datetime.date(2000, 1, 1),
                                          end_date=datetime.date(2001, 1, 1))
        lp = factories.LoanProfileV1Factory()
        bor = factories.BorrowerV1Factory(loan_profile=lp)
        bor.previous_addresses.add(addr)
        self.assertEqual(bor.years_of_residence_history, 1.0)

    def test_with_start_date_only(self):
        addr = factories.AddressV1Factory(start_date=datetime.date(2000, 1, 1),
                                          end_date=None)
        lp = factories.LoanProfileV1Factory()
        bor = factories.BorrowerV1Factory(loan_profile=lp)
        bor.previous_addresses.add(addr)
        # test that an empty end_date will be interpreted as datetime.today()
        self.assertTrue(bor.years_of_residence_history > 16)

    def test_with_end_date_only(self):
        addr = factories.AddressV1Factory(start_date=None,
                                          end_date=datetime.date(2000, 1, 1))
        lp = factories.LoanProfileV1Factory()
        bor = factories.BorrowerV1Factory(loan_profile=lp)
        bor.previous_addresses.add(addr)
        # if there is no start date it will be interpreted as 0
        self.assertEqual(bor.years_of_residence_history, 0)


class TestMortgageLiabilities(TestCase):
    def test_success(self):
        mortgage_1 = factories.MortgageLoanLiabilityFactory(
            account_identifier='123xyz',
            holder_name='giant financial')
        dup_mortage_1 = factories.MortgageLoanLiabilityFactory(
            account_identifier=mortgage_1.account_identifier,
            holder_name=mortgage_1.holder_name)
        mortgage_2 = factories.MortgageLoanLiabilityFactory()
        liabilities = [factories.InstallmentLiabilityFactory(), mortgage_1]
        lp = factories.LoanProfileV1Factory()
        bor = factories.BorrowerV1Factory(loan_profile=lp)
        cob = factories.CoborrowerV1Factory(borrower=bor)
        bor.liabilities.add(mortgage_2, *liabilities)
        cob.liabilities.add(dup_mortage_1, *liabilities)

        mortgages = lp.get_mortgage_liabilities()
        self.assertEqual(len(mortgages), 2)

        # if two mortgage contain the same values for holder_name and account_identifier
        # there is no way to know which mortage will be returned
        self.assertTrue((mortgage_1 in mortgages) or (dup_mortage_1 in mortgages))
        self.assertFalse((mortgage_1 in mortgages) and (dup_mortage_1 in mortgages))
        self.assertTrue(mortgage_2 in mortgages)


class TestPropertyPurposeUpdateFromMortgageProfile(TestCase):
    def assertResolvePropertyPurpose(self, plans_value, occupy_value, purpose_exp):
        loan_profile = factories.LoanProfileV1Factory(
            property_purpose='')
        borrower = factories.BorrowerV1Factory(
            loan_profile=loan_profile,
            demographics=factories.DemographicsV1Factory(
                plans_to_occupy_as_primary_residence=plans_value))
        mortgage_profile = MortgageProfileRefinanceFactory(
            property_occupation=occupy_value)
        self.assertEqual(loan_profile.property_purpose, '')
        result = loan_profile._resolve_property_purpose(mortgage_profile)
        msg = "declaration = '{}'; occupation = '{}'; expected '{}' instead of '{}'".format(
            borrower.demographics.plans_to_occupy_as_primary_residence,
            mortgage_profile.property_occupation,
            purpose_exp,
            result)
        self.assertEqual(result, purpose_exp, msg)

    def test_primary_residence_from_demographics(self):
        dm_none = None
        dm_true = True
        dm_false = False
        mp_primary = MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES.primary
        mp_investment = MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES.investment
        mp_secondary = MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES.secondary
        lp_primary = LoanProfileV1.sample_PROPERTY_PURPOSES.primary_residence
        lp_investment = LoanProfileV1.sample_PROPERTY_PURPOSES.investor
        lp_secondary = LoanProfileV1.sample_PROPERTY_PURPOSES.second_home
        test_cases = (
            (dm_none, mp_primary, lp_primary),
            (dm_none, mp_investment, lp_investment),
            (dm_none, mp_secondary, lp_secondary),
            (dm_false, mp_primary, lp_primary),
            (dm_false, mp_investment, lp_investment),
            (dm_false, mp_secondary, lp_secondary),
            (dm_true, mp_primary, lp_primary),
            (dm_true, mp_investment, lp_primary),
            (dm_true, mp_secondary, lp_primary))
        for test_case_params in test_cases:
            self.assertResolvePropertyPurpose(*test_case_params)


class TestDemographicsRaceField(TestCase):
    def test_default_is_empty_array(self):
        d = DemographicsV1.objects.create()
        self.assertEqual(d.race, [])
        self.assertIsNone(d.full_clean())

    def test_empty_values_not_ok(self):
        empty_values = ('', {}, ())
        d = DemographicsV1.objects.create()
        msg = "{'race': [u'This field cannot be blank.']}"
        for value in empty_values:
            d.race = value
            with self.assertRaisesMessage(ValidationError, msg):
                d.full_clean()

    def test_null_not_ok(self):
        d = DemographicsV1(race=None)
        msg = "{'race': [u'This field cannot be null.']}"
        with self.assertRaisesMessage(ValidationError, msg):
            d.full_clean()

    def test_invalid_values_fail(self):
        msg = u'Item 0 in the array did not validate: [u"Value \'{0}\' is not a valid choice."]'

        invalid_values = ['hi', 'white']
        for value in invalid_values:
            d = DemographicsV1.objects.create(race=[value])
            try:
                d.full_clean()
            except ValidationError as e:
                expected = [msg.format(value)]
                self.assertEqual(e.messages, expected)

    def test_must_be_an_array(self):
        d = DemographicsV1(race='hi')
        with self.assertRaises(DataError):
            d.save()

    def test_saves_value(self):
        d = DemographicsV1.objects.create(race=['White', 'BlackOrAfricanAmerican'])
        self.assertIsNone(d.full_clean())
        self.assertEqual(d.race, ['White', 'BlackOrAfricanAmerican'])


class TestPurposeOfLoanV1Mixin(TestCase):
    def test_default_value_for_estate_will_be_held(self):
        lp = LoanProfileV1.objects.create()
        self.assertEqual(lp.how_estate_will_be_held, 'fee_simple')

    def test_invalid_value_for_estate_will_be_held(self):
        msg = u"Value 'bogusInput' is not a valid choice."
        lp = factories.LoanProfileV1Factory(
            how_estate_will_be_held='bogusInput',
            respa_triggered_at=datetime.date(year=2016, month=1, day=1),
            other_on_loan='no',
            lock_owner_updated=datetime.datetime.today())
        with self.assertRaisesMessage(ValidationError, msg):
            lp.full_clean()
