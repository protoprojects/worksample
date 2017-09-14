import datetime
import logging
import mock

from django.core.urlresolvers import reverse
from django.test import TestCase

from accounts.models import Customer
from accounts.factories import AdvisorFactory
from accounts.tests.helpers import JWTAuthAPITestCase
from contacts.models import ContactRequestMortgageProfile
from contacts import factories as contact_factories
from core.utils import LogMutingTestMixinBase
from core.models import Recaptcha
from loans.models import LoanProfileV1
from mortgage_profiles.models import MortgageProfile, MortgageProfilePurchase, MortgageProfileRefinance
from vendors.serializers import SalesforceOpportunitySerializer
from vendors.sf_push import SalesforcePush, SalesforceLoanProfileMapper

logger = logging.getLogger("sample.vendors.test_serializers")


class VendorLogMutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.vendors.serializer']


class SalesforceOpportunitySerializerTests(VendorLogMutingMixin, TestCase):
    """
    Should handle JSON opportunitys and create loan profiles.
    """
    def setUp(self):
        self.advisor = AdvisorFactory()
        self.opportunity = {
            'id': '123abc',
            'owner': {
                'email': self.advisor.email,
            },
            'loan__type__c': 'Purchase',
            'property_type__c': 'Single Family Residence',
            'property__value__c': 17505500,
            'down__payment__amt__c': 1000000,
            'property__zip__code__c': '94111',
            'first__time__buyer__c': 'Yes',
            'length_of_ownership__c': 'Long-term (Over 15 years)',
            'opportunity_contact_roles': {
                'records': [{
                    'contact': {
                        'first_name': 'Jotest',
                        'last_name': 'Do',
                        'email': 'jodo@example.com',
                        'birthdate__c': '1950-01-01',
                        'years__in__school__c': 4,
                        'marital__status__c': 'Separated',
                        'phone': '415-555-1212',
                        'citizenship__c': 'US Citizen',
                        'mailing_address': {
                            'city': 'San Francisco',
                            'state': 'California',
                            'street': '123 Testing Street',
                            'postal_code': '94111'
                        }
                    }
                }]
            }
        }
        super(SalesforceOpportunitySerializerTests, self).setUp()

    def test_serializer_validates_valid_opportunity(self):
        """Should create loan profile."""
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))


class SalesforcePurchaseTests(VendorLogMutingMixin, TestCase):
    def test_build_full_profile_success(self):
        opportunity = {
            'id': 'lead-id-1234',
            'owner': {
                'email': AdvisorFactory().email
            },
            'loan__type__c': 'Purchase',
            'property__use__c': 'Primary Home',
            'property__address__c': '695 Harbor St',
            'property__city__c': 'Morro Bay',
            'propery__state__c': 'CA',
            'property__zip__code__c': '93442',
            'property__value__c': 125000.0,
            'down__payment__amt__c': 25000.0,
            'first__time__buyer__c': 'Yes',
            'length_of_ownership__c': 'Long-term (Over 15 years)',
            'opportunity_contact_roles': {
                'records': [{
                    'contact': {
                        'first_name': 'BoboFirst',
                        'last_name': 'BoboLast',
                        'email': 'bobo@example.com',
                        'birthdate__c': '1955-07-17',
                        'years__in__school__c': 32,
                        'marital__status__c': 'Single',
                        'phone': '312-555-1212',
                        'citizenship__c': 'Non Permanent Resident Alien',
                        'mailing_address': {
                            'street': '1 Infinite Loop',
                            'city': 'Cupertino',
                            'state_code': 'CA',
                            'postal_code': '95014'
                        }
                    }
                }]
            }
        }
        serializer = SalesforceOpportunitySerializer(data=opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        validated_data = serializer.save()
        lp_guid = serializer.loan_profile.guid
        lp = LoanProfileV1.objects.get(guid=lp_guid)
        borr = lp.borrowers.first()
        mail_addr = borr.mailing_address
        mp = lp.mortgage_profiles.select_subclasses().first()

        # Added fields
        self.assertEqual(validated_data['sample-guid'], lp_guid)
        self.assertEqual(validated_data['sample-guid'], lp_guid)
        # Loan Profile
        self.assertEqual('purchase', lp.purpose_of_loan)
        self.assertIsNotNone(lp.lead)
        self.assertEqual('lead-id-1234', lp.lead.lead_id)
        self.assertEqual('Salesforce', lp.lead.name)
        # Borrower
        self.assertEqual(1, lp.borrowers.count())
        self.assertEqual('BoboFirst', borr.first_name)
        self.assertEqual('BoboLast', borr.last_name)
        self.assertEqual('bobo@example.com', borr.email)
        self.assertEqual('non_permanent_resident_alien', borr.citizenship_status)
        self.assertEqual('unmarried', borr.marital_status)
        self.assertEqual('312-555-1212', borr.home_phone)
        self.assertEqual(32, borr.years_in_school)
        self.assertEqual(datetime.date(1955, 7, 17), borr.dob)
        self.assertIsNotNone(borr.mailing_address)
        # Borrower Mailing Address
        self.assertEqual('1 Infinite Loop', mail_addr.street)
        self.assertEqual('Cupertino', mail_addr.city)
        self.assertEqual('CA', mail_addr.state)
        self.assertEqual('95014', mail_addr.postal_code)
        # MortgageProfile
        self.assertEqual(1, lp.mortgage_profiles.count())
        self.assertIsNotNone(mp)
        self.assertIsInstance(mp, MortgageProfilePurchase)

    def test_build_minimal_profile_returns_success(self):
        advisor = AdvisorFactory()
        opportunity = {
            'id': 'lead-id-1234',
            'owner': {
                'email': advisor.email
            },
            'loan__type__c': 'Purchase',
            'opportunity_contact_roles': {
                'records': [{
                    'contact': {
                        'first_name': 'BoboFirst',
                        'last_name': 'BoboLast',
                        'email': 'bobo@example.com',
                    }
                }]
            }
        }
        serializer = SalesforceOpportunitySerializer(data=opportunity)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        lp_guid = serializer.loan_profile.guid
        lp = LoanProfileV1.objects.get(guid=lp_guid)
        borr = lp.borrowers.first()
        mp = lp.mortgage_profiles.select_subclasses().first()

        # Response
        self.assertEqual(serializer.loan_profile.guid, lp_guid)
        # Advisor
        self.assertEqual(lp.advisor.email, advisor.email)
        # Borrower
        self.assertEqual(1, lp.borrowers.count())
        self.assertEqual('BoboFirst', borr.first_name)
        self.assertEqual('BoboLast', borr.last_name)
        self.assertEqual('bobo@example.com', borr.email)
        # MortgageProfile
        self.assertEqual(1, lp.mortgage_profiles.count())
        self.assertIsInstance(mp, MortgageProfilePurchase)

    def test_missing_required_fields_returns_errors(self):
        opportunity = {
            'id': 'lead-id-1234',
            'owner': {
            },
            'loan__type__c': 'Purchase',
            'opportunity_contact_roles': {
                'records': [{
                    'contact': {
                        'last_name': 'BoboLast',
                        'email': 'bobo@example.com',
                    }
                }]
            }
        }
        serializer = SalesforceOpportunitySerializer(data=opportunity)
        errors = {
            'owner': {
                'email': [u'This field is required.']},
            'opportunity_contact_roles': {
                'records': [
                    {'contact': {
                        'first_name': [u'This field is required.']}}]}}
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, errors)


class SalesforceOpportunitySerializerNullTests(TestCase):

    def setUp(self):
        advisor = AdvisorFactory()
        self.opportunity = {
            'attributes': None,
            'cash__out__c': False,
            # below to be added in
            # 'property__use__c'
            # 'property__address__c'
            # 'property__city__c'
            # 'propery__state__c'
            # 'property__zip__code__c'
            'id': 'oppid',
            'loan__type__c': 'Purchase',
            'opportunity_contact_roles': {
                'done': True,
                'records': [{
                    'attributes': None,
                    'contact': {
                        'attributes': None,
                        'email': 'test@email.com',
                        'first_name': 'MAP',
                        'id': None,
                        'last_name': 'test1',
                        # 'mailing_address' to be added in
                        'other_address': None,
                        'record_type_id': None,
                        'veteran__c': None
                    },
                    'contact_id': None,
                    'id': None,
                    'opportunity_id': None
                }],
                'total_size': 1
            },
            'owner': {
                'attributes': None,
                'email': advisor.email,
                'id': None
            },
            'owner_id': None,
            'property__state__c': None,
            'record_type_id': '012G0000001YfDdIAK',
        }

    def test_serializer_validates_with_null_mailing_address(self):
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.borrower.first_name, 'MAP')

    def test_serializer_validates_with_mailing_address_with_null_values(self):
        mailing_address = {
            'city': None,
            'country': "United States",
            'country_code': "US",
            'geocode_accuracy': None,
            'latitude': None,
            'longitude': None,
            'postal_code': None,
            'state': None,
            'state_code': None,
            'street': None
        }
        self.opportunity['opportunity_contact_roles']['records'][0]['contact']['mailing_address'] = mailing_address
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.borrower.first_name, 'MAP')

    def test_serializer_is_valid_with_null_for_property_address(self):
        self.opportunity.update({
            'property__address__c': None,
            'property__city__c': None,
            'propery__state__c': None,
            'property__zip__code__c': None,
            'property__county__c': None,
        })
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.borrower.first_name, 'MAP')
        self.assertIsNone(serializer.loan_profile.new_property_address)

        self.assertEqual(serializer.mortgage_profile.property_state, '')
        self.assertEqual(serializer.mortgage_profile.property_zipcode, '')
        self.assertEqual(serializer.mortgage_profile.property_county, '')

    def test_invalid_citizenship_saves_empty_string(self):
        self.opportunity['opportunity_contact_roles']['records'][0]['contact']['citizenship__c'] = 'not valid'
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.borrower.citizenship_status, '')

    def test_invalid_state_code_does_not_save(self):
        self.opportunity['property__address__c'] = '9232 Harmony Rd'
        self.opportunity['property__state__c'] = 'not valid'
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.loan_profile.new_property_address.street, '9232 Harmony Rd')
        self.assertIsNone(serializer.loan_profile.new_property_address.state)

    def test_invalid_property_use_saves_empty_string(self):
        self.opportunity['loan__type__c'] = 'Refinance'
        self.opportunity['property__use__c'] = 'invalid'
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.loan_profile.property_purpose, '')
        self.assertEqual(serializer.mortgage_profile.property_occupation, '')

    def test_negative_years_in_school_saves_null(self):
        self.opportunity['opportunity_contact_roles']['records'][0]['contact']['years__in__school__c'] = -1
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertIsNone(serializer.borrower.years_in_school)

    def test_invalid_choice_for_first_time_buyer_saves_null(self):
        self.opportunity['first__time__buyer__c'] = 'invalid'
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertIsNone(serializer.borrower.is_purchase_first_time_buyer)

    def test_valid_choice_for_first_time_buyer_saves(self):
        self.opportunity['first__time__buyer__c'] = 'Yes'
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertTrue(serializer.borrower.is_purchase_first_time_buyer)

    def test_cash_out_amount_is_null_when_cash_out_is_false(self):
        self.opportunity['loan__type__c'] = 'Refinance'
        self.opportunity['cash__out__c'] = False
        self.opportunity['cash__out__amount__c'] = 1000
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertFalse(serializer.loan_profile.is_cash_out)
        self.assertIsNone(serializer.loan_profile.cash_out_amount)

    def test_cash_out_amount_saves_when_cash_out_is_true(self):
        self.opportunity['loan__type__c'] = 'Refinance'
        self.opportunity['cash__out__c'] = True
        self.opportunity['cash__out__amount__c'] = 1000
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertTrue(serializer.loan_profile.is_cash_out)
        self.assertEqual(serializer.loan_profile.cash_out_amount, 1000)

    def test_invalid_loan_type_saves(self):
        self.opportunity['loan__type__c'] = 'invalid'
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.loan_profile.purpose_of_loan, '')

    def test_null_loan_type_saves(self):
        self.opportunity['loan__type__c'] = None
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertEqual(serializer.loan_profile.purpose_of_loan, '')

    def test_negative_dependents_count_sets_has_dependents_to_none(self):
        self.opportunity['opportunity_contact_roles']['records'][0]['contact']['dependents__c'] = -1
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertIsNone(serializer.borrower.has_dependents_ages)
        self.assertEqual(serializer.borrower.dependents_ages, '')

    def test_zero_dependents_count_sets_has_dependents_to_false(self):
        self.opportunity['opportunity_contact_roles']['records'][0]['contact']['dependents__c'] = 0
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertFalse(serializer.borrower.has_dependents_ages)
        self.assertEqual(serializer.borrower.dependents_ages, '')

    def test_two_dependents_count_sets_has_dependents_to_true(self):
        self.opportunity['opportunity_contact_roles']['records'][0]['contact']['dependents__c'] = 2
        self.opportunity['opportunity_contact_roles']['records'][0]['contact']['age_of__dependents__c'] = '12,4'
        serializer = SalesforceOpportunitySerializer(data=self.opportunity)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.assertTrue(serializer.borrower.has_dependents_ages)
        self.assertEqual(serializer.borrower.dependents_ages, '12,4')


class TestSalesforceMixin(TestCase):

    """common infra for salesforce tests"""
    # pylint: disable=no-self-use
    def setUp(self):
        recaptcha = Recaptcha.get_solo()
        recaptcha.enable = False
        recaptcha.save()

    def _create_purchase_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'researching_options',
            'purchase_type': 'first_time_homebuyer',
            'property_occupation': 'my_current_residence',
            'property_type': 'single_family',
            'target_value': 1200000,
            'purchase_down_payment': 240000,
        }
        response = self.client.post(reverse('mortgage_profiles:purchase_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfilePurchase)
        return mp

    def _create_alt_purchase_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'offer_submitted',
            'purchase_type': 'vacation_home',
            'property_occupation': 'second_home_vacation_home',
            'property_type': 'two_unit',
            'target_value': 1500000,
            'purchase_down_payment': 300000,
        }
        response = self.client.post(reverse('mortgage_profiles:purchase_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfilePurchase)
        return mp

    def _create_rate_refi_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.REFINANCE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'investment_property',
            'property_type': 'condo_less_5',
            'purpose': 'lower_mortgage_payments',
            'mortgage_owe': 10000,
            'cashout_amount': 10000,
            'property_value': 1200000,
        }
        response = self.client.post(reverse('mortgage_profiles:refinance_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfileRefinance)
        return mp

    def _create_cashout_refi_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.REFINANCE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'investment_property',
            'property_type': 'condo_less_5',
            'purpose': 'cash_out',
            'mortgage_owe': 10000,
            'cashout_amount': 10000,
            'property_value': 1200000,
        }
        response = self.client.post(reverse('mortgage_profiles:refinance_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfileRefinance)
        return mp

    def _create_new_form_purchase_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'researching_options',
            'purchase_type': 'first_time_homebuyer',
            'property_type': 'single_family',
            'target_value': 1200000,
            'purchase_down_payment': 240000,
            'adjustable_rate_comfort': 'no',
            'rate_preference': 'fixed',
            'credit_score': '650'
        }
        response = self.client.post(reverse('mortgage_profiles:purchase_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfilePurchase)
        return mp

    def _create_new_form_alt_purchase_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'offer_submitted',
            'purchase_type': 'vacation_home',
            'property_type': 'two_unit',
            'target_value': 1500000,
            'purchase_down_payment': 300000,
            'adjustable_rate_comfort': 'yes',
            'rate_preference': 'variable',
            'credit_score': '740'
        }
        response = self.client.post(reverse('mortgage_profiles:purchase_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfilePurchase)
        return mp

    def _create_new_form_refi_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.REFINANCE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'investment_property',
            'property_type': 'condo_less_5',
            'mortgage_owe': 10000,
            'cashout_amount': 10000,
            'property_value': 1200000,
            'adjustable_rate_comfort': 'unsure',
            'rate_preference': 'variable',
            'credit_score': '800',
        }
        response = self.client.post(reverse('mortgage_profiles:refinance_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfileRefinance)
        return mp

    def _create_new_form_rate_refi_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.REFINANCE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'investment_property',
            'property_type': 'condo_less_5',
            'purpose': 'lower_mortgage_payments',
            'mortgage_owe': 10000,
            'cashout_amount': 10000,
            'property_value': 1200000,
            'adjustable_rate_comfort': 'unsure',
            'rate_preference': 'variable',
            'credit_score': '800',
        }
        response = self.client.post(reverse('mortgage_profiles:refinance_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfileRefinance)
        return mp

    def _create_new_form_cashout_refi_mortgage_profile(self):
        data = {
            'kind': MortgageProfile.REFINANCE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'investment_property',
            'property_type': 'condo_less_5',
            'purpose': 'cash_out',
            'mortgage_owe': 10000,
            'cashout_amount': 10000,
            'property_value': 1200000,
            'adjustable_rate_comfort': 'unsure',
            'rate_preference': 'variable',
            'credit_score': 800,
        }
        response = self.client.post(reverse('mortgage_profiles:refinance_list'), data, format='json')
        mp = MortgageProfile.objects.filter(uuid=response.data.get('id')).select_subclasses().first()
        self.assertIsInstance(mp, MortgageProfileRefinance)
        return mp

    # pylint: disable=no-self-use
    @mock.patch('vendors.tasks.SalesforceLoanProfileMapper.push')
    def test_salesforce_loan_sent(self, mocked_push):
        logger.debug('SF-LOAN-PATCHED-PUSH')

    @mock.patch('vendors.tasks.push_loan_dict_to_salesforce.apply_async')
    def test_salesforce_dict_push(self, mocked_push):
        logger.debug('SF-LOAN-PATCHED-DICT-PUSH')

    @mock.patch('vendors.tasks.push_lead_to_salesforce.apply_async')
    def test_salesforce_cr_push(self, mocked_push):
        logger.debug('SF-LOAN-PATCHED-CR-PUSH')


class TestSalesforceContactRequest(TestSalesforceMixin, TestCase):
    """
    Basic tests for ContactRequest Purchase serializers
    """

    def _create_contact_request(self, mortgage_profile_id, mortgage_profile_kind):
        data = {
            'first_name': 'Test',
            'last_name': 'Test',
            'phone': '5555555555',
            'email': mortgage_profile_kind+'_anonymous@asdf.com',
            'mortgage_profile_id': mortgage_profile_id
        }

        self.assertFalse(ContactRequestMortgageProfile.objects.filter(email=data['email']).exists())
        self.client.post(reverse('contact_requests:mortgage_profile_list'), data, format='json')
        self.assertTrue(ContactRequestMortgageProfile.objects.filter(email=data['email']).exists())
        cr = ContactRequestMortgageProfile.objects.get(email=data['email'])
        return cr

    def _test_common_serialized_data(self, serialized_data):
        self.assertIsNotNone(serialized_data)
        self.assertIsNotNone(serialized_data['LastName'])
        self.assertIsNotNone(serialized_data['FirstName'])
        self.assertEqual("RateQuote", serialized_data['Medium__c'])
        self.assertEqual("English", serialized_data['Lead_Preferred_language__c'])
        self.assertEqual("005G00000076Hs8", serialized_data['OwnerId'])
        self.assertEqual("Site", serialized_data['Lead_Source_Details__c'])
        self.assertEqual("sample Organic RateQuote", serialized_data['LeadSource'])
        self.assertFalse('Credit_Score__c' in serialized_data)
        self.assertEqual("Priority", serialized_data['Lead_Priority__c'])

    @mock.patch('vendors.sf_push.SalesforcePush.push')
    def test_contact_request_no_mortgage_profile(self, sf_push_mock):
        contact = contact_factories.ContactRequestMortgageProfileFactory(
            first_name='Test',
            last_name='Testy',
            phone='5555555555',
        )
        sfp = SalesforcePush(contact.id)
        self._test_common_serialized_data(sfp.serializer.data)
        self.assertEqual('Test', sfp.serializer.data['FirstName'])
        self.assertEqual('Testy', sfp.serializer.data['LastName'])
        self.assertEqual('5555555555', sfp.serializer.data['Phone'])

    @mock.patch('vendors.sf_push.SalesforcePush.push')
    def test_cashout_refi_serialization(self, sf_push_mock):
        profile = self._create_cashout_refi_mortgage_profile()
        contact = self._create_contact_request(profile.uuid, profile.kind)
        sfp = SalesforcePush(contact.id)
        self._test_common_serialized_data(sfp.serializer.data)
        self.assertEqual('Test', sfp.serializer.data['FirstName'])
        self.assertEqual('Test', sfp.serializer.data['LastName'])
        self.assertEqual('5555555555', sfp.serializer.data['Phone'])
        self.assertEqual(20000, sfp.serializer.data['Loan_Amount__c'])
        self.assertEqual(1200000, sfp.serializer.data['Property_Value__c'])
        self.assertEqual('refinance_anonymous@asdf.com', sfp.serializer.data['Email'])
        self.assertEqual('Investment Property', sfp.serializer.data['Property_Use__c'])
        self.assertEqual(10000, sfp.serializer.data['ExistingLiens__c'])
        self.assertEqual(10000, sfp.serializer.data['Loan_Balance__c'])
        self.assertEqual('cash_out', sfp.serializer.data['Refinance_Reason__c'])

    @mock.patch('vendors.sf_push.SalesforcePush.push')
    def test_rate_refi_serialization(self, sf_push_mock):
        profile = self._create_rate_refi_mortgage_profile()
        contact = self._create_contact_request(profile.uuid, profile.kind)
        sfp = SalesforcePush(contact.id)
        self._test_common_serialized_data(sfp.serializer.data)
        self.assertEqual('Test', sfp.serializer.data['FirstName'])
        self.assertEqual('Test', sfp.serializer.data['LastName'])
        self.assertEqual('5555555555', sfp.serializer.data['Phone'])
        self.assertEqual(10000, sfp.serializer.data['Loan_Amount__c'])
        self.assertEqual(1200000, sfp.serializer.data['Property_Value__c'])
        self.assertEqual('refinance_anonymous@asdf.com', sfp.serializer.data['Email'])
        self.assertEqual('Investment Property', sfp.serializer.data['Property_Use__c'])
        self.assertEqual(10000, sfp.serializer.data['ExistingLiens__c'])
        self.assertEqual(10000, sfp.serializer.data['Loan_Balance__c'])
        self.assertEqual('lower_mortgage_payments', sfp.serializer.data['Refinance_Reason__c'])

    @mock.patch('vendors.sf_push.SalesforcePush.push')
    def test_purchase_serialization(self, sf_push_mock):
        profile = self._create_purchase_mortgage_profile()
        contact = self._create_contact_request(profile.uuid, profile.kind)
        sfp = SalesforcePush(contact.id)
        self._test_common_serialized_data(sfp.serializer.data)
        self.assertEqual('Test', sfp.serializer.data['FirstName'])
        self.assertEqual('Test', sfp.serializer.data['LastName'])
        self.assertEqual('5555555555', sfp.serializer.data['Phone'])
        self.assertEqual('Single Family Residence', sfp.serializer.data['Property_Type__c'])
        self.assertEqual('purchase', sfp.serializer.data['Loan_Purpose__c'])
        self.assertEqual(960000, sfp.serializer.data['Loan_Amount__c'])
        self.assertEqual('purchase_anonymous@asdf.com', sfp.serializer.data['Email'])
        self.assertEqual('Primary Home', sfp.serializer.data['Property_Use__c'])
        self.assertEqual(240000, sfp.serializer.data['Down_Payment_Amt__c'])

    @mock.patch('vendors.sf_push.SalesforcePush.push')
    def test_alt_purchase_serialization(self, sf_push_mock):
        profile = self._create_alt_purchase_mortgage_profile()
        contact = self._create_contact_request(profile.uuid, profile.kind+'1')
        sfp = SalesforcePush(contact.id)
        self._test_common_serialized_data(sfp.serializer.data)
        self.assertEqual('2-4 Unit', sfp.serializer.data['Property_Type__c'])
        self.assertEqual('purchase', sfp.serializer.data['Loan_Purpose__c'])
        self.assertEqual(1200000, sfp.serializer.data['Loan_Amount__c'])
        self.assertEqual('purchase1_anonymous@asdf.com', sfp.serializer.data['Email'])
        self.assertEqual('Second Home', sfp.serializer.data['Property_Use__c'])
        self.assertEqual(300000, sfp.serializer.data['Down_Payment_Amt__c'])


class TestSalesforceLoanProfile(JWTAuthAPITestCase, TestSalesforceMixin, TestCase):
    """LPv1 Test cases"""
    def _create_loan_profile(self):
        response = self.client.post(reverse('cp:registration'), data={
            'first_name': 'Jill',
            'last_name': 'Upthehill',
            'phone': '301 964 0381',
            'phone_kind': 'mobile',
            'email': 'test@example.com',
            'password': 'Validp4sword!',
            'same_password': 'Validp4sword!',
        })
        self.assertEqual(response.status_code, 201)
        customer = Customer.objects.get(email='test@example.com')
        return customer.loan_profilesv1.first()

    def _create_alt_purchase_lpv1(self):
        self._create_new_form_alt_purchase_mortgage_profile()
        lp = self._create_loan_profile()
        return lp

    def _create_purchase_lpv1(self):
        self._create_new_form_purchase_mortgage_profile()
        lp = self._create_loan_profile()
        return lp

    def _create_rate_refi_lpv1(self):
        self._create_new_form_rate_refi_mortgage_profile()
        lp = self._create_loan_profile()
        return lp

    def _create_cashout_refi_lpv1(self):
        self._create_new_form_cashout_refi_mortgage_profile()
        lp = self._create_loan_profile()
        return lp

    def _test_common_serialized_data(self, serialized_data):
        self.assertIsNotNone(serialized_data)
        self.assertIsNotNone(serialized_data['sampleID__c'])
        self.assertIsNotNone(serialized_data['LastName'])
        self.assertIsNotNone(serialized_data['FirstName'])
        self.assertEqual("PreQual", serialized_data['Medium__c'])
        self.assertEqual("English", serialized_data['Lead_Preferred_language__c'])
        self.assertEqual("005G00000076Hs8", serialized_data['OwnerId'])
        self.assertEqual("Site", serialized_data['Lead_Source_Details__c'])
        self.assertEqual("sample Organic sampleOne", serialized_data['LeadSource'])
        self.assertEqual("True", serialized_data['Pardot_Created__c'])
        self.assertFalse(serialized_data['DoNotCall'])
        self.assertFalse(serialized_data['HasOptedOutOfEmail'])
        self.assertTrue('Credit_Score__c' in serialized_data)
        self.assertEqual("Special", serialized_data['Lead_Priority__c'])
        self.assertEqual(None, serialized_data['EmploymentStatus__c'])

    @mock.patch('vendors.tasks.push_loan_dict_to_salesforce.apply_async')
    def test_purchase_lpv1(self, sf_push_mock):
        lp = self._create_purchase_lpv1()
        sflpp = SalesforceLoanProfileMapper(lp)
        self.assertIsNotNone(sflpp)
        sd = sflpp.translate()
        self._test_common_serialized_data(sd)
        self.assertEqual("No", sd['ARMComfort__c'])
        self.assertEqual('fixed', sd['RatePreference__c'])
        self.assertEqual('Single Family Residence', sd['Property_Type__c'])
        self.assertEqual(960000, sd['Loan_Amount__c'])
        self.assertEqual(650, sd['Credit_Score__c'])
        self.assertEqual(240000, sd['Down_Payment_Amt__c'])
        self.assertEqual(1200000, sd['Property_Value__c'])
        self.assertEqual('purchase', sd['Loan_Purpose__c'])

    @mock.patch('vendors.tasks.push_loan_dict_to_salesforce.apply_async')
    def test_alt_purchase_lpv1(self, sf_push_mock):
        lp = self._create_alt_purchase_lpv1()
        sflpp = SalesforceLoanProfileMapper(lp)
        self.assertIsNotNone(sflpp)
        sd = sflpp.translate()
        self._test_common_serialized_data(sd)
        self.assertEqual("Yes", sd['ARMComfort__c'])
        self.assertEqual('variable', sd['RatePreference__c'])
        self.assertEqual('2-4 Unit', sd['Property_Type__c'])
        self.assertEqual(1200000, sd['Loan_Amount__c'])
        self.assertEqual(740, sd['Credit_Score__c'])
        self.assertEqual(300000, sd['Down_Payment_Amt__c'])
        self.assertEqual(1500000, sd['Property_Value__c'])
        self.assertEqual('purchase', sd['Loan_Purpose__c'])

    @mock.patch('vendors.tasks.push_loan_dict_to_salesforce.apply_async')
    def test_cashout_refi_lpv1(self, sf_push_mock):
        lp = self._create_cashout_refi_lpv1()
        sflpp = SalesforceLoanProfileMapper(lp)
        self.assertIsNotNone(sflpp)
        sd = sflpp.translate()
        self._test_common_serialized_data(sd)
        self.assertEqual('Not Sure', sd['ARMComfort__c'])
        self.assertEqual('variable', sd['RatePreference__c'])
        self.assertEqual('Condo', sd['Property_Type__c'])
        self.assertEqual(20000, sd['Loan_Amount__c'])
        self.assertEqual(800, sd['Credit_Score__c'])
        self.assertEqual('refinance', sd['Loan_Purpose__c'])
        self.assertEqual(10000, sd['Loan_Balance__c'])
        self.assertEqual('cash_out', sd['Refinance_Reason__c'])

    @mock.patch('vendors.tasks.push_loan_dict_to_salesforce.apply_async')
    def test_rate_refi_lpv1(self, sf_push_mock):
        lp = self._create_rate_refi_lpv1()
        sflpp = SalesforceLoanProfileMapper(lp)
        self.assertIsNotNone(sflpp)
        sd = sflpp.translate()
        self._test_common_serialized_data(sd)
        self.assertEqual('Not Sure', sd['ARMComfort__c'])
        self.assertEqual('variable', sd['RatePreference__c'])
        self.assertEqual('Condo', sd['Property_Type__c'])
        self.assertEqual(10000, sd['Loan_Amount__c'])
        self.assertEqual(800, sd['Credit_Score__c'])
        self.assertEqual('refinance', sd['Loan_Purpose__c'])
        self.assertEqual(10000, sd['Loan_Balance__c'])
        self.assertEqual('lower_mortgage_payments', sd['Refinance_Reason__c'])

    @mock.patch('vendors.tasks.push_loan_dict_to_salesforce.apply_async')
    def test_update_lpv1(self, sf_push_mock):
        lp = self._create_rate_refi_lpv1()
        sflpp = SalesforceLoanProfileMapper(lp)
        self.assertIsNotNone(sflpp)
        sd = sflpp.translate()
        self.assertFalse(hasattr(sd, 'Id'))
        lp.crm_id = '0v10000TEST'
        sflpp = SalesforceLoanProfileMapper(lp)
        self.assertIsNotNone(sflpp)
        sd = sflpp.translate()
        self.assertEqual('0v10000TEST', sd['Id'])
