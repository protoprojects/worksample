"""
Utility classes and methods for handling Salesforce api data.
"""
import logging

from django.conf import settings

from core.parsers import camel_to_underscore as transform
from mortgage_profiles.models import MortgageProfile

logger = logging.getLogger("sample.vendors.utils")

# Opportunity Names
LOAN_TYPE = transform('Loan_Type__c')
# Property (some are both loan and mortgage profile)
PROPERTY_USE = transform('Property_Use__c')
PROPERTY_STREET = transform('Property_Address__c')
PROPERTY_CITY = transform('Property_City__c')
PROPERTY_STATE = transform('Property_State__c')  # this is actually a state code coming from SF
PROPERTY_ZIPCODE = transform('Property_Zip_Code__c')
# Mortgage Profile
LOAN_AMOUNT = transform('Loan_Amount__c')
PROPERTY_TYPE = transform('Property_type__c')
PROPERTY_COUNTY = transform('Property_County__c')
DOWN_PAYMENT_AMT = transform('Down_Payment_Amt__c')
PROPERTY_VALUE = transform('Property_Value__c')
LOAN_BALANCE = transform('Loan_Balance__c')
CASH_OUT = transform('Cash_Out__c')
CASH_OUT_AMT = transform('Cash_Out_Amount__c')
PURCHASE_TIMING = transform('Purchase_Timing__c')
OWNERSHIP_TIME = transform('Length_of_ownership__c')
# Referrer
REFERRED_BY = transform('Referred_by__c')
REFERRED_BY_CUSTOMER = transform('Referred_by_Customer__c')
REFERRED_BY_EMPLOYEE = transform('Referred_by_Employee__c')
REFERRED_BY_MA = transform('Referred_by_MA__c')
# Borrower
ESTIMATED_CREDIT_SCORE_RANGE = transform('Estimated_Credit_Score_Range__c')
FIRST_TIME_BUYER = transform('First_Time_Buyer__c')
IMPOUND_ESCROW = transform('Impound_Escrow__c')
COBORROWER_EMAIL = transform('Coborrower_Email__c')
COBORROWER_FIRST_NAME = transform('Coborrower_First_Name__c')
COBORROWER_LAST_NAME = transform('Coborrower_Last_Name__c')

# Contact Names
FIRST_NAME = transform('FirstName')
LAST_NAME = transform('LastName')
BIRTH_DATE = transform('Birthdate__c')
CITIZENSHIP = transform('Citizenship__c')
MARITAL_STATUS = transform('Marital_Status__c')
IS_VETERAN = transform('Veteran__c')
YEARS_IN_SCHOOL = transform('Years_In_School__c')
DEPENDENTS_COUNT = transform('Dependents__c')
DEPENDENT_AGES = transform('Age_of_Dependents__c')
MONTHLY_DEBTS = transform('Monthly_Debts_Obligations__c')
MONTHLY_INCOME = transform('Monthly_Household_Income__c')

# Utility Names
CONTACT_ROLES = transform('OpportunityContactRoles')
RECORDS_FIELD = transform('records')
CONTACT_FIELD = transform('Contact')


# Mappings
CITIZENSHIP_CHOICES = {
    'US Citizen': 'us_citizen',
    'Permanent Resident Alien': 'permanent_resident_alien',
    'Non Permanent Resident Alien': 'non_permanent_resident_alien',
    'Foreign National': 'foreign_national',
    'Other': 'other',
    None: '',
}

LOAN_TYPE_PURCHASE = 'Purchase'

LOAN_TYPE_REFINANCE = 'Refinance'

LP_PURPOSE_OF_LOAN_CHOICES = {
    LOAN_TYPE_PURCHASE: 'purchase',
    LOAN_TYPE_REFINANCE: 'refinance'}

LP_PROPERTY_USE_CHOICES = {
    'Primary Home': 'primary_residence',
    'Secondary Home': 'secondary_residence',
    'Investment Property': 'investment',
    None: '',
}

MARITAL_STATUS_CHOICES = {
    'Single': 'unmarried',
    'Widowed': 'unmarried',
    'Divorced': 'unmarried',
    'Married': 'married',
    'Separated': 'separated',
    None: None,
}


MP_PROPERTY_USE_CHOICES = {
    'Primary Home': 'my_current_residence',
    'Secondary Home': 'second_home_vacation_home',
    'Investment Property': 'investment_property',
    None: ''
}

MP_PROPERTY_TYPE_CHOICES = {
    choice: choice
    for choice, _v in MortgageProfile.PROPERTY_TYPE_CHOICES}


YES_NO_CHOICES = {
    'Yes': True,
    'No': False,
    None: None,
}

FIRST_TIME_BUYER_CHOICES = YES_NO_CHOICES

OWNERSHIP_TIME_CHOICES = {
    'Long-term (Over 15 years)': 'long_term',
    'Medium-term (5-15 years)': 'medium_term',
    'Short-term (Only a few years)': 'short_term',
    'Not sure': 'not_sure'
}

PURCHASE_TIMING_CHOICES = {
    'Not sure/just researching': 'researching_options',
    'Buying in the next 3 months': 'buying_in_3_months',
    'House in mind/offer submitted': 'offer_submitted',
    'Purchase contract in hand': 'contract_in_hand'
}


def contact_extract(opportunity):
    '''Extract the contact from an opportunity without raising an exception'''
    roles = opportunity.get(CONTACT_ROLES, {})
    records = roles.get(RECORDS_FIELD, []) if isinstance(roles, dict) else {}
    first_item = records[0] if records and isinstance(records, list) else {}
    return first_item.get(CONTACT_FIELD, {})


def _address_factory(address):
    # below fields can be found on AddressV1
    if address is None:
        return {}
    address = {
        'street': address.get('street'),  # blank=True, null=True
        'city': address.get('city'),  # blank=True, null=True
        'state': address.get('state_code'),  # blank=True, null=True
        'postal_code': address.get('postal_code')}  # blank=True, null=True
    return address if any(address.values()) else {}


def borrower_factory(opportunity):
    # opportunity is passed, instead of contact, since we need first_time_buyer
    contact = contact_extract(opportunity)
    citizenship_status = CITIZENSHIP_CHOICES.get(contact.get(CITIZENSHIP), '')  # cannot be null see below
    marital_status = MARITAL_STATUS_CHOICES.get(contact.get(MARITAL_STATUS))  # can be null see below
    first_time_buyer = FIRST_TIME_BUYER_CHOICES.get(opportunity.get(FIRST_TIME_BUYER))  # can be null see below
    dependents_count = contact.get(DEPENDENTS_COUNT)
    if (dependents_count < 0) or (dependents_count is None):
        has_dependents_ages = None
    else:
        has_dependents_ages = (0 < dependents_count)

    dependents_ages = (contact.get(DEPENDENT_AGES, '') if has_dependents_ages else '')

    years_in_school = contact.get(YEARS_IN_SCHOOL) if contact.get(YEARS_IN_SCHOOL) >= 0 else None
    # below fields can be found on BorrowerBaseV1
    borrower = {
        'first_name': contact.get('first_name'),  # required field, cannot be null
        'last_name': contact.get('last_name'),  # required field, cannot be null
        'dob': contact.get(BIRTH_DATE),  # blank=True, null=True
        'years_in_school': years_in_school,  # blank=True, null=True
        'marital_status': marital_status,  # blank=True, null=True
        'email': contact.get('email'),  # required field, cannot be null
        'home_phone': contact.get('phone'),  # blank=True, null=True
        'citizenship_status': citizenship_status,  # blank=True
        'is_veteran': contact.get(IS_VETERAN),  # NullBooleanField
        'has_dependents_ages': has_dependents_ages,  # NullBooleanField
        'dependents_ages': dependents_ages,  # blank=True
        'referral': 'other',
        'is_purchase_first_time_buyer': first_time_buyer,  # NullBooleanField
        'is_mailing_address_same': False}
    return borrower if any(borrower.values()) else {}


def borrower_mailing_address_factory(opportunity):
    contact = contact_extract(opportunity)
    return _address_factory(contact.get('mailing_address', {}))


def coborrower_factory(opportunity):
    # below fields can be found on BorrowerBaseV1
    coborrower = {
        'first_name': opportunity.get(COBORROWER_FIRST_NAME),  # blank=True, null=True
        'last_name': opportunity.get(COBORROWER_LAST_NAME),  # blank=True, null=True
        'email': opportunity.get(COBORROWER_EMAIL)  # blank=True, null=True
    }
    return coborrower if any(coborrower.values()) else {}


def property_address_factory(opportunity):
    # below fields can be found on AddressV1
    property_state = opportunity.get(PROPERTY_STATE)
    if property_state not in settings.STATE_CODES:
        property_state = None
    address = {
        'street': opportunity.get(PROPERTY_STREET),  # blank=True, null=True
        'city': opportunity.get(PROPERTY_CITY),  # blank=True, null=True
        'state': property_state,  # blank=True, null=True
        'postal_code': opportunity.get(PROPERTY_ZIPCODE)}  # blank=True, null=True
    return address if any(address.values()) else {}


def loan_profile_factory(opportunity):
    purpose_of_loan = LP_PURPOSE_OF_LOAN_CHOICES.get(opportunity.get(LOAN_TYPE), '')  # cannot be null, see below
    property_purpose = LP_PROPERTY_USE_CHOICES.get(opportunity.get(PROPERTY_USE), '')  # cannot be null, see below
    # below fields can be found on LoanProfilePurposeOfLoanMixinV1
    loan_profile = {
        'purpose_of_loan': purpose_of_loan,  # blank=True
        'property_purpose': property_purpose,  # blank=True
        'base_loan_amount': opportunity.get(LOAN_AMOUNT)  # blank=True, null=True
    }
    if purpose_of_loan == 'refinance':
        is_cash_out = opportunity.get(CASH_OUT)
        loan_profile.update({'is_cash_out': is_cash_out})  # NullBooleanField
        if is_cash_out:
            loan_profile.update({'cash_out_amount': opportunity.get(CASH_OUT_AMT)})  # NullBooleanField
    elif purpose_of_loan == 'purchase':
        loan_profile.update({
            'down_payment_amount': opportunity.get(DOWN_PAYMENT_AMT),  # blank=True, null=True
            'new_property_info_contract_purchase_price': opportunity.get(PROPERTY_VALUE)  # blank=True, null=True
        })
    return loan_profile if any(loan_profile.values()) else {}


def mortgage_profile_factory(opportunity):
    kind = opportunity.get(LOAN_TYPE)  # cannot be null required=True on MortgageProfile
    property_type = MP_PROPERTY_TYPE_CHOICES.get(opportunity.get(PROPERTY_TYPE), '')  # cannot be null, see below
    property_county = opportunity.get(PROPERTY_COUNTY, '') or ''  # or replaces a None with ''
    property_state = opportunity.get(PROPERTY_STATE, '')
    if property_state not in settings.STATE_CODES:
        property_state = ''
    property_zipcode = opportunity.get(PROPERTY_ZIPCODE, '') or ''  # or replaces a None with ''
    # below fields can be found on MortgageProfile
    profile = {
        'property_type': property_type,  # blank=True
        'property_county': property_county,  # blank=True
        'property_state': property_state,  # blank=True
        'property_zipcode': property_zipcode,  # blank=True
        'ownership_time': OWNERSHIP_TIME_CHOICES.get(opportunity.get(OWNERSHIP_TIME), '')  # blank=True
    }
    if kind == LOAN_TYPE_PURCHASE:
        profile.update({
            'kind': kind,
            'purchase_down_payment': opportunity.get(DOWN_PAYMENT_AMT),  # null=True
            'target_value': opportunity.get(PROPERTY_VALUE),  # null=True
            'purchase_timing': PURCHASE_TIMING_CHOICES.get(opportunity.get(PURCHASE_TIMING), '')})  # blank=True
    elif kind == LOAN_TYPE_REFINANCE:
        property_occupation = MP_PROPERTY_USE_CHOICES.get(opportunity.get(PROPERTY_USE), '')  # cannot be null see below
        profile.update({
            'kind': kind,
            'property_occupation': property_occupation,  # blank=True
            'property_value': opportunity.get(PROPERTY_VALUE),  # null=True
            'mortgage_owe': opportunity.get(LOAN_BALANCE),  # null=True
            'cashout_amount': opportunity.get(CASH_OUT_AMT)})  # null=True
    else:
        profile = {}
        logger.warning('VENDORS-MORTGAGE-PROFILE-FACTORY-KIND-UNKNOWN %s', kind)
    return profile if any(profile.values()) else {}
