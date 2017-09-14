# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from accounts import factories as accounts_factories
from loans.models import BorrowerV1, CoborrowerV1

from advisor_portal.serializers.loan_profile_v1 import (
    AdvisorLoanProfileV1ComplexSerializer, ContactV1Serializer,
    DemographicsV1Serializer,
)


DATA = {}
POL_DATA = {
    # purpose of loan
    'down_payment_amount': 100500,
    'down_payment_source': 'Savings',
    'is_already_in_contract': True,
    'is_cash_out': True,
    'is_down_payment_subordinate_finances_used': True,
    'new_property_address': {
        'street': 'test', 'city': 'test', 'state': 'CA', 'postal_code': '12345', 'country': 'test',
    },
    'new_property_info_contract_purchase_price': 100500,
    'property_purpose': 'Primary Home',
    'purpose_of_loan': 'purchase',
    'refinance_amount_of_existing_liens': 100500,
    'refinance_original_cost': 100500,
    'refinance_year_acquired': 2005,
}

BORROWER_BASE_DATA = {
    'current_service_status': 'test',
    'demographics': {
        'ethnicity': 'Native American',
        'gender': 'Male',
        'has_been_obligated_on_resulted_in_foreclosure_loan': False,
        'has_declared_bankruptcy_within_past_seven_years': False,
        'has_outstanding_judgements': False,
        'has_ownership_interest_in_property_last_three_years': False,
        'has_property_foreclosed_within_past_seven_years': False,
        'is_any_part_of_downpayment_borrowed': False,
        'is_comaker_or_endorser_on_note': False,
        'is_delinquent_on_debt_presently': False,
        'is_demographics_questions_request_confirmed': False,
        'is_obligated_to_pay_alimony_or_separate_maintenance': False,
        'is_party_to_lawsuit': False,
        'is_permanent_resident_alien': False,
        'is_us_citizen': True,
        'owned_property_title_hold': 'test',
        'owned_property_type': 'test',
        'plans_to_occupy_as_primary_residence': True,
        'race': ["White"],
    },
    'dependents_ages': '1,2,3,4',
    'dob': '1990-12-12',
    'email': 'test@test.com',
    'expense': [
        {'kind': 'First Mortgage', 'value': 100500, 'name': 'expense1', 'description': 'expense1'},
        {'kind': 'Other', 'value': 100500, 'name': 'expense2', 'description': 'expense2'},
    ],
    'first_name': 'test',
    'has_additional_income_sources': True,
    'has_additional_property': True,
    'has_been_student_in_last_two_years': False,
    'holding_assets': [
        {'name': 'test', 'quantity': 100500, 'symbol': 'test', 'cusip': 'test', 'current_value': 100500,
         'institution_name': 'test1', 'kind': 'test',
         'institution_address': {'street': 'test',
                                 'city': 'test', 'state': 'CA', 'postal_code': '12345', 'country': 'test'}}
    ],
    'home_phone': '12345',
    'income': [
        {'kind': 'Base', 'name': 'test', 'value': 100500, 'description': 'test', 'use_automated_process': False},
    ],
    'insurance_assets': [
        {'kind': 'Life Insurance', 'name': 'test', 'value': 100500},
    ],
    'is_first_va_loan': True,
    'is_purchase_first_time_buyer': False,
    'is_self_employed': True,
    'is_veteran': False,
    'last_name': 'test',
    'mailing_address': {
        'street': 'test', 'city': 'test', 'state': 'CA', 'postal_code': '12345', 'country': 'test'
    },
    'marital_status': 'unmarried',
    'middle_name': 'test',
    'previous_addresses': [
        {'street': 'test1', 'city': 'test1', 'state': 'CA', 'postal_code': '12345', 'country': 'test1'},
        {'street': 'test2', 'city': 'test2', 'state': 'CA', 'postal_code': '12345', 'country': 'test2'},
    ],
    'previous_employment': [
        {
            'address': {'street': 'test1', 'city': 'test1', 'state': 'CA', 'postal_code': '12345', 'country': 'test1'},
            'c_corp_percent': 10,
            'company_address': {'street': 'test1', 'city': 'test1', 'state': 'CA', 'postal_code': '12345',
                                'country': 'test1'},
            'company_entity_type': 'test',
            'company_name': 'test',
            'company_other_entity_type': 'test',
            'end_date': '1990-12-12',
            'is_employee_of_company': False,
            'phone': '12345',
            's_corp_percent': 10,
            'start_date': '1980-12-12',
            'title': 'test',
            'years_in_field': '12',
        }
    ],
    'realtor': {
        'first_name': 'test',
        'last_name': 'test',
        'company_name': 'test',
        'address': {'street': 'test', 'city': 'test', 'state': 'CA', 'postal_code': '12345', 'country': 'test'},
        'email': 'test@test.com',
        'phone': '12345',
    },
    'receives_va_disability': False,
    'rent_or_own': True,
    'role': 'test',
    'service_branch': 'test',
    'ssn': '123-45-6789',
    'title_name': 'test t. test',
    'vehicle_assets': [
        {'make': 'test', 'model': 'test', 'year': '1990', 'value': 100500, }
    ],
    'years_in_school': 12,
    'years_in_service': 12,
}

BORROWER_DATA = BORROWER_BASE_DATA.copy()
BORROWER_DATA.update({
    'ordering': 1,
    'current_property_type': 'test',
    'is_current_property_in_contract': True,
    'is_current_property_owner': True,
    'is_current_property_plans_to_sell': True,
    'is_current_property_second_or_rental': True,
    'will_current_property_sold_by_close': False,
})

COBORROWER_DATA = BORROWER_BASE_DATA.copy()
COBORROWER_DATA.update({
    'living_together_two_years': True,
})

DATA.update(POL_DATA)
DATA.update({
    'borrower': BORROWER_DATA
})
DATA.update({
    'coborrower': COBORROWER_DATA
})


class TestAdvisorLoanProfileV1ComplexSerializer(TestCase):
    def setUp(self):
        self.advisor = accounts_factories.AdvisorFactory()

    def assertPurposeOfLoanData(self, obj):
        self.assertEqual(obj.property_purpose, 'Primary Home')
        self.assertEqual(obj.purpose_of_loan, 'purchase')
        self.assertEqual(obj.refinance_original_cost, 100500)
        self.assertEqual(obj.refinance_year_acquired, 2005)
        self.assertEqual(obj.down_payment_amount, 100500)
        self.assertEqual(obj.is_already_in_contract, True)
        self.assertEqual(obj.refinance_amount_of_existing_liens, 100500)
        self.assertEqual(obj.is_cash_out, True)
        self.assertEqual(obj.down_payment_source, 'Savings')
        self.assertEqual(obj.new_property_info_contract_purchase_price, 100500)
        self.assertEqual(obj.is_down_payment_subordinate_finances_used, True)
        self.assertEqual(obj.new_property_address.street, 'test')
        self.assertEqual(obj.new_property_address.city, 'test')
        self.assertEqual(obj.new_property_address.state, 'CA')
        self.assertEqual(obj.new_property_address.postal_code, '12345')
        self.assertEqual(obj.new_property_address.country, 'test')

    # pylint: disable=too-many-statements
    def assertBorrowerData(self, borrower_obj):
        if isinstance(borrower_obj, BorrowerV1):
            self.assertEqual(borrower_obj.ordering, 1)
            self.assertEqual(borrower_obj.current_property_type, 'test')
            self.assertEqual(borrower_obj.is_current_property_in_contract, True)
            self.assertEqual(borrower_obj.is_current_property_owner, True)
            self.assertEqual(borrower_obj.is_current_property_plans_to_sell, True)
            self.assertEqual(borrower_obj.is_current_property_second_or_rental, True)
            self.assertEqual(borrower_obj.will_current_property_sold_by_close, False)

        if isinstance(borrower_obj, CoborrowerV1):
            self.assertEqual(borrower_obj.living_together_two_years, True)

        self.assertEqual(borrower_obj.last_name, 'test')
        self.assertEqual(borrower_obj.is_veteran, False)
        self.assertEqual(borrower_obj.has_additional_property, True)
        self.assertEqual(borrower_obj.has_additional_income_sources, True)
        self.assertEqual(borrower_obj.receives_va_disability, False)
        self.assertEqual(borrower_obj.is_first_va_loan, True)
        self.assertEqual(borrower_obj.years_in_school, 12)
        self.assertEqual(borrower_obj.has_been_student_in_last_two_years, False)
        self.assertEqual(borrower_obj.middle_name, 'test')
        self.assertEqual(borrower_obj.service_branch, 'test')
        self.assertEqual(borrower_obj.is_purchase_first_time_buyer, False)
        self.assertEqual(borrower_obj.first_name, 'test')
        self.assertEqual(borrower_obj.rent_or_own, True)
        self.assertEqual(borrower_obj.current_service_status, 'test')
        self.assertEqual(borrower_obj.dob, datetime.date(year=1990, day=12, month=12))
        self.assertEqual(borrower_obj.is_self_employed, True)
        self.assertEqual(borrower_obj.marital_status, 'unmarried')
        self.assertEqual(borrower_obj.ssn, '123-45-6789')
        self.assertEqual(borrower_obj.title_name, 'test t. test')
        self.assertEqual(borrower_obj.role, 'test')
        self.assertEqual(borrower_obj.home_phone, '12345')
        self.assertEqual(borrower_obj.dependents_ages, '1,2,3,4')
        self.assertEqual(borrower_obj.years_in_service, 12)
        self.assertEqual(borrower_obj.email, 'test@test.com')

        self.assertEqual(borrower_obj.previous_addresses.first().street, 'test1')
        self.assertEqual(borrower_obj.previous_addresses.first().city, 'test1')
        self.assertEqual(borrower_obj.previous_addresses.first().state, 'CA')
        self.assertEqual(borrower_obj.previous_addresses.first().postal_code, '12345')
        self.assertEqual(borrower_obj.previous_addresses.first().country, 'test1')
        self.assertEqual(borrower_obj.previous_addresses.last().street, 'test2')
        self.assertEqual(borrower_obj.previous_addresses.last().city, 'test2')
        self.assertEqual(borrower_obj.previous_addresses.last().state, 'CA')
        self.assertEqual(borrower_obj.previous_addresses.last().postal_code, '12345')
        self.assertEqual(borrower_obj.previous_addresses.last().country, 'test2')
        self.assertEqual(borrower_obj.mailing_address.street, 'test')
        self.assertEqual(borrower_obj.mailing_address.city, 'test')
        self.assertEqual(borrower_obj.mailing_address.state, 'CA')
        self.assertEqual(borrower_obj.mailing_address.postal_code, '12345')
        self.assertEqual(borrower_obj.mailing_address.country, 'test')

        self.assertEqual(borrower_obj.demographics.ethnicity, 'Native American')
        self.assertEqual(borrower_obj.demographics.gender, 'Male')
        self.assertEqual(borrower_obj.demographics.has_been_obligated_on_resulted_in_foreclosure_loan, False)
        self.assertEqual(borrower_obj.demographics.has_declared_bankruptcy_within_past_seven_years, False)
        self.assertEqual(borrower_obj.demographics.has_outstanding_judgements, False)
        self.assertEqual(borrower_obj.demographics.has_ownership_interest_in_property_last_three_years, False)
        self.assertEqual(borrower_obj.demographics.has_property_foreclosed_within_past_seven_years, False)
        self.assertEqual(borrower_obj.demographics.is_any_part_of_downpayment_borrowed, False)
        self.assertEqual(borrower_obj.demographics.is_comaker_or_endorser_on_note, False)
        self.assertEqual(borrower_obj.demographics.is_delinquent_on_debt_presently, False)
        self.assertEqual(borrower_obj.demographics.is_demographics_questions_request_confirmed, False)
        self.assertEqual(borrower_obj.demographics.is_obligated_to_pay_alimony_or_separate_maintenance, False)
        self.assertEqual(borrower_obj.demographics.is_party_to_lawsuit, False)
        self.assertEqual(borrower_obj.demographics.is_permanent_resident_alien, False)
        self.assertEqual(borrower_obj.demographics.is_us_citizen, True)
        self.assertEqual(borrower_obj.demographics.owned_property_title_hold, 'test')
        self.assertEqual(borrower_obj.demographics.owned_property_type, 'test')
        self.assertEqual(borrower_obj.demographics.plans_to_occupy_as_primary_residence, True)
        self.assertEqual(borrower_obj.demographics.race, ['White'])

        self.assertEqual(borrower_obj.expense.first().kind, 'First Mortgage')
        self.assertEqual(borrower_obj.expense.first().value, 100500)
        self.assertEqual(borrower_obj.expense.first().name, 'expense1')
        self.assertEqual(borrower_obj.expense.first().description, 'expense1')
        self.assertEqual(borrower_obj.expense.last().kind, 'Other')
        self.assertEqual(borrower_obj.expense.last().value, 100500)
        self.assertEqual(borrower_obj.expense.last().name, 'expense2')
        self.assertEqual(borrower_obj.expense.last().description, 'expense2')

        self.assertEqual(borrower_obj.holding_assets.first().name, 'test')
        self.assertEqual(borrower_obj.holding_assets.first().quantity, 100500)
        self.assertEqual(borrower_obj.holding_assets.first().symbol, 'test')
        self.assertEqual(borrower_obj.holding_assets.first().cusip, 'test')
        self.assertEqual(borrower_obj.holding_assets.first().kind, 'test')
        self.assertEqual(borrower_obj.holding_assets.first().current_value, 100500)
        self.assertEqual(borrower_obj.holding_assets.first().institution_address.street, 'test')
        self.assertEqual(borrower_obj.holding_assets.first().institution_address.city, 'test')
        self.assertEqual(borrower_obj.holding_assets.first().institution_address.state, 'CA')
        self.assertEqual(borrower_obj.holding_assets.first().institution_address.postal_code, '12345')
        self.assertEqual(borrower_obj.holding_assets.first().institution_address.country, 'test')

        self.assertEqual(borrower_obj.realtor.first_name, 'test')
        self.assertEqual(borrower_obj.realtor.last_name, 'test')
        self.assertEqual(borrower_obj.realtor.company_name, 'test')
        self.assertEqual(borrower_obj.realtor.email, 'test@test.com')
        self.assertEqual(borrower_obj.realtor.phone, '12345')
        self.assertEqual(borrower_obj.realtor.address.street, 'test')
        self.assertEqual(borrower_obj.realtor.address.city, 'test')
        self.assertEqual(borrower_obj.realtor.address.state, 'CA')
        self.assertEqual(borrower_obj.realtor.address.postal_code, '12345')
        self.assertEqual(borrower_obj.realtor.address.country, 'test')

        self.assertEqual(borrower_obj.income.first().kind, 'Base')
        self.assertEqual(borrower_obj.income.first().name, 'test')
        self.assertEqual(borrower_obj.income.first().value, 100500)
        self.assertEqual(borrower_obj.income.first().description, 'test')
        self.assertEqual(borrower_obj.income.first().use_automated_process, False)

        self.assertEqual(borrower_obj.insurance_assets.first().kind, 'Life Insurance')
        self.assertEqual(borrower_obj.insurance_assets.first().name, 'test')
        self.assertEqual(borrower_obj.insurance_assets.first().value, 100500)

        self.assertEqual(borrower_obj.vehicle_assets.first().make, 'test')
        self.assertEqual(borrower_obj.vehicle_assets.first().model, 'test')
        self.assertEqual(borrower_obj.vehicle_assets.first().year, '1990')
        self.assertEqual(borrower_obj.vehicle_assets.first().value, 100500)

        self.assertEqual(borrower_obj.previous_employment.first().company_other_entity_type, 'test')
        self.assertEqual(borrower_obj.previous_employment.first().phone, '12345')
        self.assertEqual(borrower_obj.previous_employment.first().c_corp_percent, 10)
        self.assertEqual(borrower_obj.previous_employment.first().years_in_field, 12)
        self.assertEqual(borrower_obj.previous_employment.first().end_date, datetime.date(year=1990, day=12, month=12))
        self.assertEqual(borrower_obj.previous_employment.first().s_corp_percent, 10)
        self.assertEqual(borrower_obj.previous_employment.first().title, 'test')
        self.assertEqual(borrower_obj.previous_employment.first().is_employee_of_company, False)
        self.assertEqual(borrower_obj.previous_employment.first().company_name, 'test')
        self.assertEqual(borrower_obj.previous_employment.first().company_entity_type, 'test')
        self.assertEqual(borrower_obj.previous_employment.first().start_date, datetime.date(year=1980,
                                                                                            day=12, month=12))
        self.assertEqual(borrower_obj.previous_employment.first().address.street, 'test1')
        self.assertEqual(borrower_obj.previous_employment.first().address.city, 'test1')
        self.assertEqual(borrower_obj.previous_employment.first().address.state, 'CA')
        self.assertEqual(borrower_obj.previous_employment.first().address.postal_code, '12345')
        self.assertEqual(borrower_obj.previous_employment.first().address.country, 'test1')
        self.assertEqual(borrower_obj.previous_employment.first().company_address.street, 'test1')
        self.assertEqual(borrower_obj.previous_employment.first().company_address.city, 'test1')
        self.assertEqual(borrower_obj.previous_employment.first().company_address.state, 'CA')
        self.assertEqual(borrower_obj.previous_employment.first().company_address.postal_code, '12345')
        self.assertEqual(borrower_obj.previous_employment.first().company_address.country, 'test1')

    def test_successful_objects_creation_with_coborrower(self):
        s = AdvisorLoanProfileV1ComplexSerializer(data=DATA)
        self.assertTrue(s.is_valid())
        obj = s.save(advisor_id=self.advisor.id)
        borrower_obj = obj.borrowers.first()
        self.assertPurposeOfLoanData(obj)
        self.assertBorrowerData(borrower_obj)
        self.assertBorrowerData(borrower_obj.coborrower)

    def test_successful_objects_creation_without_coborrower(self):
        data_without_coborrower = DATA.copy()
        data_without_coborrower.pop('coborrower')
        s = AdvisorLoanProfileV1ComplexSerializer(data=data_without_coborrower)
        self.assertTrue(s.is_valid())
        obj = s.save(advisor_id=self.advisor.id)
        borrower_obj = obj.borrowers.first()
        self.assertPurposeOfLoanData(obj)
        self.assertBorrowerData(borrower_obj)
        with self.assertRaises(ObjectDoesNotExist):
            _ = borrower_obj.coborrower

    def test_passing_coborrower_data_without_borrower_data_is_not_passing_validation(self):
        data_without_borrower = DATA.copy()
        data_without_borrower.pop('borrower')
        s = AdvisorLoanProfileV1ComplexSerializer(data=data_without_borrower)
        self.assertFalse(s.is_valid())
        self.assertEqual(
            s.errors['non_field_errors'][0],
            'Both borrower and coborrower data must be provided for coborrower creation.'
        )


class TestNullableFields(TestCase):
    def test_none_values_are_valid_for_nullable_charfield(self):
        s = ContactV1Serializer(data={
            'first_name': None,
            'email': None,
        })
        self.assertTrue(s.is_valid())

    def test_none_values_are_valid_for_nullable_textfield(self):
        s = DemographicsV1Serializer(data={
            'is_party_to_lawsuit_explanation': None,
        })
        self.assertTrue(s.is_valid())
