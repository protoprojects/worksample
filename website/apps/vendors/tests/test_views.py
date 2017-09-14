import datetime
import json
import os

from django.conf import settings
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.factories import AdvisorFactory
from customer_portal.utils import create_customer_registration_access_code
from core.utils import LogMutingTestMixinBase, get_consumer_portal_base_url
from loans.models import LoanProfileV1
from vendors.utils import (
    CITIZENSHIP_CHOICES,
    LP_PROPERTY_USE_CHOICES,
    MARITAL_STATUS_CHOICES,
    YES_NO_CHOICES,
)

from mortgage_profiles.models import MortgageProfileRefinance, MortgageProfilePurchase

TEST_CASES_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_cases/'))


class VendorMutingTestMixin(LogMutingTestMixinBase):
    log_names = ['sample.vendors.api',
                 'sample.vendors.serializers',
                 'sample.vendors.utils',
                 'sample.vendors.views']


class TestSalesforceView(VendorMutingTestMixin, APITestCase):
    # pylint: disable=too-many-statements
    def _test_minimum_mapping(self, opportunity):
        opportunity['Owner']['Email'] = AdvisorFactory().email
        response = self.client.post(reverse('vendors:vendor_salesforce_create_view'), opportunity, format='json')
        lp_guid = response.data['sample-guid']
        lp = LoanProfileV1.objects.get(guid=lp_guid)
        borr = lp.borrowers.first()
        mp = lp.mortgage_profiles.select_subclasses().first()
        lead = lp.lead

        access_code_signature = borr.get_access_code_signature()
        direct_access_code = create_customer_registration_access_code(access_code_signature)

        # Response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['sample-guid'], lp.guid)
        self.assertEqual(response.data['sample-url'], '{}/dashboard/lp-guid/{}'.format(
            settings.ADVISOR_PORTAL_HOST, lp.guid))
        self.assertEqual(response.data['sample-registration-direct-url'], '{}/register-direct/{}'.format(
            get_consumer_portal_base_url(), direct_access_code))

        # Lead
        self.assertEqual(opportunity['Id'], lead.lead_id)
        # LoanProfile
        self.assertTrue(LoanProfileV1.objects.filter(guid=lp_guid).exists())
        self.assertIsNotNone(lp.lead)
        self.assertEqual(opportunity['Id'], lp.lead.lead_id)
        self.assertEqual('Salesforce', lp.lead.name)

        # Borrower
        self.assertEqual(1, lp.borrowers.count())
        contact = opportunity['OpportunityContactRoles']['records'][0]['Contact']
        self.assertEqual(contact['FirstName'], borr.first_name)
        self.assertEqual(contact['LastName'], borr.last_name)
        self.assertEqual(contact['Email'], borr.email)

        # Test fields that cannot be null are blank
        self.assertEqual(borr.citizenship_status, '')
        self.assertEqual(borr.dependents_ages, '')

        # Test that fiels that can be null are None
        self.assertIsNone(borr.mailing_address)
        self.assertIsNone(borr.dob)
        self.assertIsNone(borr.years_in_school)
        self.assertIsNone(borr.marital_status)
        self.assertIsNone(borr.home_phone)
        self.assertIsNone(borr.is_veteran)
        self.assertIsNone(borr.has_dependents_ages)
        self.assertIsNone(borr.is_purchase_first_time_buyer)

        if opportunity.get('Loan_Type__c') is None:
            self.assertIsNone(mp)
        else:
            self.assertEqual(1, lp.mortgage_profiles.count())
            self.assertIsNotNone(mp)

        if opportunity['Loan_Type__c'] == 'Purchase':
            self.assertIsNone(lp.down_payment_amount)
            self.assertIsNone(lp.new_property_info_contract_purchase_price)
            self.assertEqual('purchase', lp.purpose_of_loan)
            self.assertIsInstance(mp, MortgageProfilePurchase)
        elif opportunity['Loan_Type__c'] == 'Refinance':
            self.assertIsInstance(mp, MortgageProfileRefinance)
            self.assertEqual('refinance', lp.purpose_of_loan)
            self.assertIsNone(lp.is_cash_out)
            self.assertIsNone(lp.cash_out_amount)

    def _test_mapping(self, opportunity):
        opportunity['Owner']['Email'] = AdvisorFactory().email
        response = self.client.post(reverse('vendors:vendor_salesforce_create_view'), opportunity, format='json')
        lp_guid = response.data['sample-guid']
        lp = LoanProfileV1.objects.get(guid=lp_guid)
        borr = lp.borrowers.first()
        coborr = borr.coborrower
        mp = lp.mortgage_profiles.select_subclasses().first()
        lead = lp.lead

        access_code_signature = borr.get_access_code_signature()
        direct_access_code = create_customer_registration_access_code(access_code_signature)

        # Response data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['sample-guid'], lp.guid)
        self.assertEqual(response.data['sample-url'], '{}/dashboard/lp-guid/{}'.format(
            settings.ADVISOR_PORTAL_HOST, lp.guid))
        self.assertEqual(response.data['sample-registration-direct-url'], '{}/register-direct/{}'.format(
            get_consumer_portal_base_url(), direct_access_code))
        # Lead
        self.assertEqual(opportunity['Id'], lead.lead_id)
        # LoanProfile
        self.assertTrue(LoanProfileV1.objects.filter(guid=lp_guid).exists())
        self.assertIsNotNone(lp.lead)
        self.assertEqual(opportunity['Id'], lp.lead.lead_id)
        self.assertEqual(opportunity['Loan_Amount__c'], lp.base_loan_amount)
        self.assertEqual(LP_PROPERTY_USE_CHOICES.get(opportunity['Property_Use__c']), lp.property_purpose)
        self.assertEqual('Salesforce', lp.lead.name)
        # LoanProfile.new_property_adddress
        self.assertEqual(lp.new_property_address.street, opportunity['Property_Address__c'])
        self.assertEqual(lp.new_property_address.city, opportunity['Property_City__c'])
        self.assertEqual(lp.new_property_address.state, opportunity['Property_State__c'])
        self.assertEqual(lp.new_property_address.postal_code, opportunity.get('Property_Zip_Code__c'))
        # Borrower
        self.assertEqual(1, lp.borrowers.count())
        contact = opportunity['OpportunityContactRoles']['records'][0]['Contact']
        self.assertEqual(contact['FirstName'], borr.first_name)
        self.assertEqual(contact['LastName'], borr.last_name)
        self.assertEqual(contact['Email'], borr.email)
        self.assertEqual(CITIZENSHIP_CHOICES.get(contact['Citizenship__c']), borr.citizenship_status)
        self.assertEqual(MARITAL_STATUS_CHOICES.get(contact['Marital_Status__c']), borr.marital_status)
        self.assertEqual(contact['Phone'], borr.home_phone)
        self.assertEqual(contact['Years_In_School__c'], borr.years_in_school)
        self.assertEqual(contact['Age_of_Dependents__c'], borr.dependents_ages)
        self.assertEqual(contact['Veteran__c'], borr.is_veteran)
        self.assertEqual(bool(int(contact['Dependents__c'])), borr.has_dependents_ages)
        self.assertEqual(datetime.date(1990, 7, 7), borr.dob)
        self.assertIsNotNone(borr.mailing_address)
        # Coborrower
        self.assertEqual(opportunity['Coborrower_First_Name__c'], coborr.first_name)
        self.assertEqual(opportunity['Coborrower_Last_Name__c'], coborr.last_name)
        self.assertEqual(opportunity['Coborrower_Email__c'], coborr.email)
        # Borrower Mailing Address
        address = contact['MailingAddress']
        self.assertEqual(address['street'], borr.mailing_address.street)
        self.assertEqual(address['city'], borr.mailing_address.city)
        self.assertEqual(address['stateCode'], borr.mailing_address.state)
        self.assertEqual(address['postalCode'], borr.mailing_address.postal_code)
        # MortgageProfile
        if opportunity.get('Loan_Type__c') is None:
            self.assertIsNone(mp)
        else:
            self.assertEqual(1, lp.mortgage_profiles.count())
            self.assertIsNotNone(mp)

        if opportunity['Loan_Type__c'] == 'Purchase':
            self.assertEqual(YES_NO_CHOICES.get(opportunity['First_Time_Buyer__c']), borr.is_purchase_first_time_buyer)
            self.assertEqual(opportunity['Down_Payment_Amt__c'], lp.down_payment_amount)
            self.assertEqual(opportunity['Property_Value__c'], lp.new_property_info_contract_purchase_price)
            self.assertEqual('purchase', lp.purpose_of_loan)
            self.assertIsInstance(mp, MortgageProfilePurchase)
        elif opportunity['Loan_Type__c'] == 'Refinance':
            self.assertIsInstance(mp, MortgageProfileRefinance)
            self.assertEqual('refinance', lp.purpose_of_loan)
            is_cash_out = opportunity['Cash_Out__c']
            self.assertEqual(is_cash_out, lp.is_cash_out)
            if is_cash_out:
                self.assertEqual(opportunity['Cash_Out_Amount__c'], lp.cash_out_amount)
            else:
                self.assertIsNone(lp.cash_out_amount)

    def test_bad_request(self):
        response = self.client.post(reverse('vendors:vendor_salesforce_create_view'), {}, format='json')
        required_fields = ['owner', 'id', 'opportunity_contact_roles']
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in required_fields:
            self.assertIn(field, response.data)

    def test_invalid_advisor_email(self):
        with open(os.path.join(TEST_CASES_DIR, 'C01_refinance.json')) as test_json:
            opportunity = json.load(test_json)
        opportunity['Owner']['Email'] = 'doesnotexist@example.com'
        response = self.client.post(reverse('vendors:vendor_salesforce_create_view'), opportunity, format='json')
        error_response = {'owner': {'email': [u'advisor not found for email: doesnotexist@example.com']}}
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, error_response)

    def test_opportunity_with_no_loan_type(self):
        with open(os.path.join(TEST_CASES_DIR, 'C01_refinance.json')) as test_json:
            opportunity = json.load(test_json)
        opportunity['Loan_Type__c'] = None
        self._test_mapping(opportunity)

    def test_refinance_opportunity(self):
        with open(os.path.join(TEST_CASES_DIR, 'C01_refinance.json')) as test_json:
            opportunity = json.load(test_json)
        self._test_mapping(opportunity)

    def test_purchase_opportunity(self):
        with open(os.path.join(TEST_CASES_DIR, 'C02_purchase.json')) as test_json:
            opportunity = json.load(test_json)
        self._test_mapping(opportunity)

    def test_refinance_minimum_opportunity_with_nulls(self):
        with open(os.path.join(TEST_CASES_DIR, 'C03_refi_min_with_nulls.json')) as test_json:
            opportunity = json.load(test_json)
        self._test_minimum_mapping(opportunity)

    def test_purchase_minimum_opportunity_with_nulls(self):
        with open(os.path.join(TEST_CASES_DIR, 'C04_purchase_min_with_nulls.json')) as test_json:
            opportunity = json.load(test_json)
        self._test_minimum_mapping(opportunity)

    def test_refinance_minimum_opportunity_no_nulls(self):
        with open(os.path.join(TEST_CASES_DIR, 'C05_refi_min_no_nulls.json')) as test_json:
            opportunity = json.load(test_json)
        self._test_minimum_mapping(opportunity)

    def test_purchase_minimum_opportunity_no_nulls(self):
        with open(os.path.join(TEST_CASES_DIR, 'C06_purchase_min_no_nulls.json')) as test_json:
            opportunity = json.load(test_json)
        self._test_minimum_mapping(opportunity)
