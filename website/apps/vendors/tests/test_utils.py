from django.test import TestCase

from core.utils import FullDiffMixin

import vendors.utils


def advisor_email_extract(opportunity):
    return opportunity.get('owner', {}).get('email')  # required field, cannot be null


class FactoryTestMixin(object):
    def assertFactoryIsValid(self, data_in, factory_fn, expected, forbidden=()):
        output = factory_fn(data_in)
        for key, value in expected.items():
            self.assertIn(key, output)
            self.assertEqual(value,
                             output[key],
                             msg='Key: {}: {} != {}'.format(key, value, output[key]))
        for key in forbidden:
            self.assertNotIn(key, output)

    def assertEmptyResult(self, data_in, factory_fn):
        output = factory_fn(data_in)
        self.assertEqual(output, {})


class AdvisorEmailTestCase(TestCase):
    def test_advisor_email_success(self):
        opp = {
            'owner': {
                'email': 'advisor@example.com'}}
        email = advisor_email_extract(opp)
        self.assertEqual(email, 'advisor@example.com')

    def test_email_missing_no_throw(self):
        opp = {
            'owner': {
                'not_email': 'advisor@example.com'}}
        email = advisor_email_extract(opp)
        self.assertIsNone(email)

    def test_owner_missing_no_throw(self):
        opp = {
            'not_owner': {
                'email': 'advisor@example.com'}}
        email = advisor_email_extract(opp)
        self.assertIsNone(email)


class ContactExtractTest(TestCase):
    def test_contact_extract_success(self):
        opp = {
            vendors.utils.CONTACT_ROLES: {
                vendors.utils.RECORDS_FIELD: [{
                    vendors.utils.CONTACT_FIELD: {
                        'XYZZY': '#WINNING'}}]}}
        contact = vendors.utils.contact_extract(opp)
        self.assertIn('XYZZY', contact)
        self.assertEquals('#WINNING', contact['XYZZY'])

    def test_contact_extract_missing_roles_no_throw(self):
        opp = {
            ('not_' + vendors.utils.CONTACT_ROLES): {
                vendors.utils.RECORDS_FIELD: [{
                    vendors.utils.CONTACT_FIELD: {
                        'XYZZY': '#WINNING'}}]}}
        contact = vendors.utils.contact_extract(opp)
        self.assertEqual(contact, {})

    def test_contact_extract_missing_records_no_throw(self):
        opp = {
            vendors.utils.CONTACT_ROLES: {
                ('not_' + vendors.utils.RECORDS_FIELD): [{
                    vendors.utils.CONTACT_FIELD: {
                        'XYZZY': '#WINNING'}}]}}
        contact = vendors.utils.contact_extract(opp)
        self.assertEqual(contact, {})

    def test_contact_extract_empty_records_no_throw(self):
        opp = {
            vendors.utils.CONTACT_ROLES: {
                vendors.utils.RECORDS_FIELD: []}}
        contact = vendors.utils.contact_extract(opp)
        self.assertEqual(contact, {})

    def test_contact_extract_missing_contact_no_throw(self):
        opp = {
            vendors.utils.CONTACT_ROLES: {
                vendors.utils.RECORDS_FIELD: [{
                    ('not_' + vendors.utils.CONTACT_FIELD): {
                        'XYZZY': '#WINNING'}}]}}
        contact = vendors.utils.contact_extract(opp)
        self.assertEqual(contact, {})


class CitizenshipChoicesTestCase(TestCase):
    def testEqual(self):
        dut = vendors.utils.CITIZENSHIP_CHOICES
        sf_names = {
            'US Citizen',
            'Permanent Resident Alien',
            'Non Permanent Resident Alien',
            'Foreign National',
            'Other'}
        for name in sf_names:
            self.assertIn(name, dut)
        self.assertEqual(dut['US Citizen'], 'us_citizen')
        self.assertEqual(dut['Permanent Resident Alien'], 'permanent_resident_alien')
        self.assertEqual(dut['Non Permanent Resident Alien'], 'non_permanent_resident_alien')
        self.assertEqual(dut['Foreign National'], 'foreign_national')
        self.assertEqual(dut['Other'], 'other')
        invalid_name = 'ARGH'
        self.assertNotIn(invalid_name, dut)
        self.assertEqual(dut.get(invalid_name, ''), '')


class AddressFactoryTestCase(FactoryTestMixin, FullDiffMixin, TestCase):
    def setUp(self):
        # pylint: disable=protected-access
        self.factory = vendors.utils._address_factory

    def test_address_success(self):
        address = {
            'street': '695 Harbor St',
            'city': 'Morro Bay',
            'state_code': 'CA',
            'postal_code': '93442',
            'UNEXPECTED_KEY': 'unexpected value'}
        expected = {
            'street': '695 Harbor St',
            'city': 'Morro Bay',
            'state': 'CA',
            'postal_code': '93442'}
        forbidden = {'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(address, self.factory, expected, forbidden)

    def test_empty_address_values_empty_result(self):
        address = {
            'street': '',
            'city': '',
            'state_code': '',
            'postal_code': '',
            'UNEXPECTED_KEY': 'unexpected value'}
        self.assertEmptyResult(address, self.factory)

    def test_empty_address_empty_result(self):
        address = {
            'UNEXPECTED_KEY': 'unexpected value'}
        self.assertEmptyResult(address, self.factory)


class PropertyAddressFactoryTestCase(FactoryTestMixin, FullDiffMixin, TestCase):
    def setUp(self):
        self.factory = vendors.utils.property_address_factory

    def test_property_address(self):
        opp = {
            vendors.utils.PROPERTY_STREET: '695 Harbor St',
            vendors.utils.PROPERTY_CITY: 'Morro Bay',
            vendors.utils.PROPERTY_STATE: 'CA',
            vendors.utils.PROPERTY_ZIPCODE: '93442'}
        expected = {
            'street': '695 Harbor St',
            'city': 'Morro Bay',
            'state': 'CA',
            'postal_code': '93442'}
        self.assertFactoryIsValid(opp, self.factory, expected)

    def test_empty_property_address_empty_result(self):
        opp = {
            'UNEXPECTED_KEY': 'unexpected value'}
        self.assertEmptyResult(opp, self.factory)

    def test_empty_property_address_values_empty_result(self):
        opp = {
            vendors.utils.PROPERTY_STREET: '',
            vendors.utils.PROPERTY_CITY: '',
            vendors.utils.PROPERTY_STATE: '',
            vendors.utils.PROPERTY_ZIPCODE: '',
            'UNEXPECTED_KEY': 'Some Value'}
        self.assertEmptyResult(opp, self.factory)


class BorrowerFactoryTestCase(FactoryTestMixin, FullDiffMixin, TestCase):
    def setUp(self):
        self.factory = vendors.utils.borrower_factory

    def test_borrower_success(self):
        opportunity = {
            'opportunity_contact_roles': {
                'records': [{
                    'contact': {
                        'first_name': 'BoboFirst',
                        'last_name': 'BoboLast',
                        vendors.utils.BIRTH_DATE: '1992-10-21',
                        vendors.utils.YEARS_IN_SCHOOL: 13,
                        vendors.utils.MARITAL_STATUS: 'Married',
                        'email': 'bobo@example.com',
                        'phone': '415-555-1212',
                        vendors.utils.CITIZENSHIP: 'US Citizen',
                        vendors.utils.IS_VETERAN: 'Yes',
                    }
                }]
            }
        }

        expected = {
            'first_name': 'BoboFirst',
            'last_name': 'BoboLast',
            'dob': '1992-10-21',
            'years_in_school': 13,
            'marital_status': 'married',
            'email': 'bobo@example.com',
            'home_phone': '415-555-1212',
            'citizenship_status': 'us_citizen',
            'is_veteran': 'Yes',
        }
        self.assertFactoryIsValid(opportunity, self.factory, expected)

    def test_borrower_empty_maps_hardcoded_values(self):
        opportunity = {
            'opportunity_contact_roles': {
                'records': [{
                    'contact': {
                        'UNEXPECTED_KEY': 'unexpected value'
                    }
                }]
            }
        }
        expected_hard_coded_values = {
            'is_mailing_address_same': False,
            'referral': 'other',
        }
        self.assertFactoryIsValid(opportunity, self.factory, expected_hard_coded_values)


class CoborrowerFactoryTestCase(FactoryTestMixin, FullDiffMixin, TestCase):
    def setUp(self):
        self.factory = vendors.utils.coborrower_factory

    def test_coborrower_success(self):
        opp = {
            vendors.utils.COBORROWER_FIRST_NAME: 'CoboFirst',
            vendors.utils.COBORROWER_LAST_NAME: 'CoboLast',
            vendors.utils.COBORROWER_EMAIL: 'cobo@example.net',
            'UNEXPECTED_KEY': 'a value'}
        expected = {
            'first_name': 'CoboFirst',
            'last_name': 'CoboLast',
            'email': 'cobo@example.net'}
        forbidden = {'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(opp, self.factory, expected, forbidden)

    def test_coborrower_values_empty_success(self):
        opp = {
            vendors.utils.COBORROWER_FIRST_NAME: '',
            vendors.utils.COBORROWER_LAST_NAME: '',
            vendors.utils.COBORROWER_EMAIL: '',
            'UNEXPECTED_KEY': 'a value'}
        self.assertEmptyResult(opp, self.factory)

    def test_coborrower_empty_success(self):
        opp = {
            'UNEXPECTED_KEY': 'a value'}
        self.assertEmptyResult(opp, self.factory)


class LoanProfileFactoryTestCase(FactoryTestMixin, FullDiffMixin, TestCase):
    def setUp(self):
        self.factory = vendors.utils.loan_profile_factory

    def test_loan_profile_purchase_success(self):
        opp = {
            vendors.utils.LOAN_TYPE: 'Purchase',
            vendors.utils.PROPERTY_USE: 'Secondary Home',
            'UNEXPECTED_KEY': 'a value'}
        expected = {
            'purpose_of_loan': 'purchase',
            'property_purpose': 'secondary_residence'}
        forbidden = {'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(opp, self.factory, expected, forbidden)

    def test_loan_profile_refinance_success(self):
        opp = {
            vendors.utils.LOAN_TYPE: 'Refinance',
            vendors.utils.PROPERTY_USE: 'Investment Property',
            'UNEXPECTED_KEY': 'a value'}
        expected = {
            'purpose_of_loan': 'refinance',
            'property_purpose': 'investment'}
        forbidden = {'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(opp, self.factory, expected, forbidden)

    def test_loan_profile_unknown_type_not_used(self):
        opp = {
            vendors.utils.LOAN_TYPE: 'XYZZY Unknown Type',
            vendors.utils.PROPERTY_USE: 'Secondary Home',
            'UNEXPECTED_KEY': 'a value'}
        expected = {
            'purpose_of_loan': '',
            'property_purpose': 'secondary_residence'}
        forbidden = {'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(opp, self.factory, expected, forbidden)

    def test_loan_profile_unknown_property_use_not_used(self):
        opp = {
            vendors.utils.LOAN_TYPE: 'Refinance',
            vendors.utils.PROPERTY_USE: 'XYZZY Unknown Value',
            'UNEXPECTED_KEY': 'a value'}
        expected = {
            'purpose_of_loan': 'refinance',
            'property_purpose': ''}
        forbidden = {'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(opp, self.factory, expected, forbidden)

    def test_empty_loan_profile_values_empty_result(self):
        opp = {
            vendors.utils.LOAN_TYPE: '',
            vendors.utils.PROPERTY_USE: '',
            'UNEXPECTED_KEY': 'a value'}
        self.assertEmptyResult(opp, self.factory)

    def test_empty_loan_profile_vempty_result(self):
        opp = {
            'UNEXPECTED_KEY': 'a value'}
        self.assertEmptyResult(opp, self.factory)


class MortgageProfileFactoryTestCase(FactoryTestMixin, FullDiffMixin, TestCase):
    def setUp(self):
        self.factory = vendors.utils.mortgage_profile_factory

    def test_mortgage_profile_purchase_success(self):
        opp = {
            vendors.utils.LOAN_TYPE: vendors.utils.LOAN_TYPE_PURCHASE,
            vendors.utils.PROPERTY_TYPE: 'two_unit',
            vendors.utils.PROPERTY_COUNTY: 'San Luis Obispo',
            vendors.utils.PROPERTY_STATE: 'CA',
            vendors.utils.PROPERTY_ZIPCODE: '93442',
            vendors.utils.DOWN_PAYMENT_AMT: 25000.0,
            vendors.utils.PROPERTY_VALUE: 125000.0,
            'UNEXPECTED_KEY': 'unexpected value'}
        expected = {
            'kind': 'Purchase',
            'property_type': 'two_unit',
            'property_county': 'San Luis Obispo',
            'property_state': 'CA',
            'property_zipcode': '93442',
            'purchase_down_payment': 25000.0,
            'target_value': 125000.0}
        forbidden = {'property_occupation', 'property_value', 'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(opp, self.factory, expected, forbidden)

    def test_mortgage_profile_refinance_success(self):
        opp = {
            vendors.utils.LOAN_TYPE: vendors.utils.LOAN_TYPE_REFINANCE,
            vendors.utils.PROPERTY_TYPE: 'townhouse',
            vendors.utils.PROPERTY_COUNTY: 'San Luis Obispo',
            vendors.utils.PROPERTY_STATE: 'CA',
            vendors.utils.PROPERTY_ZIPCODE: '93442',
            vendors.utils.PROPERTY_USE: 'Primary Home',
            vendors.utils.PROPERTY_VALUE: 200000.0,
            'UNEXPECTED_KEY': 'unexpected value'}
        expected = {
            'kind': 'Refinance',
            'property_type': 'townhouse',
            'property_county': 'San Luis Obispo',
            'property_state': 'CA',
            'property_zipcode': '93442',
            'property_occupation': 'my_current_residence',
            'property_value': 200000.0}
        forbidden = {'purchase_down_payment', 'target_value', 'UNEXPECTED_KEY'}
        self.assertFactoryIsValid(opp, self.factory, expected, forbidden)

    def test_mortgage_profile_unknown_empty_result(self):
        opp = {
            vendors.utils.LOAN_TYPE: 'XYZZY Loan Type',
            vendors.utils.PROPERTY_TYPE: 'townhouse',
            vendors.utils.PROPERTY_COUNTY: 'San Luis Obispo',
            vendors.utils.PROPERTY_STATE: 'CA',
            vendors.utils.PROPERTY_ZIPCODE: '93442',
            vendors.utils.PROPERTY_USE: 'Primary Home',
            vendors.utils.PROPERTY_VALUE: 200000.0,
            'UNEXPECTED_KEY': 'unexpected value'}
        self.assertEmptyResult(opp, self.factory)
