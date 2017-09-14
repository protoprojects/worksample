import logging

from django.db import IntegrityError, transaction
from django.conf import settings

from rest_framework import serializers

from accounts.models import Advisor
from customer_portal.utils import create_customer_registration_access_code
from loans.models import AddressV1, BorrowerV1, BorrowerBaseV1, CoborrowerV1, Lead, LoanProfileV1
from mortgage_profiles.models import MortgageProfile, MortgageProfilePurchase, MortgageProfileRefinance
from vendors.utils import (
    borrower_factory,
    coborrower_factory,
    borrower_mailing_address_factory,
    loan_profile_factory,
    mortgage_profile_factory,
    property_address_factory,
)
from core.utils import get_consumer_portal_base_url

SALESFORCE_LEAD_SOURCE = 'Salesforce'
SALESFORCE_CRM_TYPE = 'salesforce'

logger = logging.getLogger("sample.vendors.serializers")


# pylint: disable=abstract-method
class _AddressSerializer(serializers.Serializer):
    city = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    state_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    street = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class _ContactSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    birthdate__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    citizenship__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    age_of__dependents__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dependents__c = serializers.IntegerField(required=False)
    mailing_address = _AddressSerializer(required=False, allow_null=True)
    marital__status__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    veteran__c = serializers.NullBooleanField(required=False)
    years__in__school__c = serializers.IntegerField(required=False, allow_null=True)


class _RecordSerializer(serializers.Serializer):
    contact = _ContactSerializer(required=True)


class _OpportunityContactRolesSerializer(serializers.Serializer):
    records = serializers.ListSerializer(child=_RecordSerializer(), required=True)


class _OwnerSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        try:
            advisor = Advisor.objects.get(email=email)
        except Advisor.DoesNotExist:
            raise serializers.ValidationError('advisor not found for email: {email}'.format(email=email))
        else:
            # advisor saved to self, to avoid fetching a second time in SalesforceOpportunitySerializer.create
            self.parent.advisor = advisor
            return email


class SalesforceOpportunitySerializer(serializers.Serializer):
    '''
    All fields in this serializer and its children will be mapped to sample.
    * if a field is submitted by Salesforce and is not represented by a Serializer Field, it will not be mapped
    * if required=True, this MUST be submitted by Salesforce or the mapping will not take places.
    '''
    # sample-guid this field is added to validated_data in .create()
    # sample-url this field is added to validated_data in .create()

    id = serializers.CharField(required=True)
    opportunity_contact_roles = _OpportunityContactRolesSerializer(required=True)

    owner = _OwnerSerializer()

    cash__out__c = serializers.NullBooleanField(required=False)
    cash__out__amount__c = serializers.IntegerField(required=False)
    down__payment__amt__c = serializers.IntegerField(required=False)
    first__time__buyer__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    length_of_ownership__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    loan__type__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    loan__amount__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    property__address__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    property__city__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    property__state__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    property__use__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    property__value__c = serializers.IntegerField(required=False)
    property__zip__code__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    property_type__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    coborrower__email__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    coborrower__first__name__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    coborrower__last__name__c = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def create(self, validated_data):
        '''
        Creates the LoanProfileV1 and associated objects from the validated_data
        * object creation is wrapped in a transaction to prevent a partial mapping
        * if successful, keys 'sample-guid' and 'sample-url' are added to the validated_data
          for use in view
        '''
        try:
            with transaction.atomic():
                prop_addr = self._create_new_property_address(validated_data)
                borr_addr = self._create_borrower_mailing_address(validated_data)

                # attributes assigned to self for testing purposes
                # pylint: disable=attribute-defined-outside-init
                self.lead = self._create_lead(validated_data)
                self.loan_profile = self._create_loan_profile(validated_data, self.advisor, self.lead, prop_addr)
                self.borrower = self._create_borrower(validated_data, self.loan_profile, borr_addr)
                self.coborrower = self._create_coborrower(validated_data, self.borrower)
                self.mortgage_profile = self._create_mortgage_profile(validated_data, self.loan_profile)
        except IntegrityError:
            logger.exception('VENDOR-SF-API-BUILD-PROFILE-EXCEPTION')
            raise serializers.ValidationError('server error: transaction failed')
        else:
            # adding on attributes 'status', 'sample-guid' and 'sample-url' which are required by the view
            logger.info('VENDOR-SF-API-BUILD-PROFILE opp: %s', self.loan_profile.crm_id)
            validated_data['sample-guid'] = self.loan_profile.guid
            validated_data['sample-url'] = '{}/dashboard/lp-guid/{}'.format(
                settings.ADVISOR_PORTAL_HOST, self.loan_profile.guid)
            access_code_signature = self.borrower.get_access_code_signature()
            direct_access_code = create_customer_registration_access_code(access_code_signature)
            validated_data['sample-registration-direct-url'] = '{}/register-direct/{}'.format(
                get_consumer_portal_base_url(), direct_access_code)
            return validated_data

    # Methods for create:
    @staticmethod
    def _create_new_property_address(opportunity):
        property_address_data = property_address_factory(opportunity)
        return (AddressV1.objects.create(**property_address_data)
                if property_address_data
                else None)

    @staticmethod
    def _create_borrower_mailing_address(opportunity):
        borrower_mailing_address_data = borrower_mailing_address_factory(opportunity)
        return (AddressV1.objects.create(**borrower_mailing_address_data)
                if borrower_mailing_address_data
                else None)

    @staticmethod
    def _create_lead(opportunity):
        return Lead.objects.create(name=SALESFORCE_LEAD_SOURCE, lead_id=opportunity['id'])

    @staticmethod
    def _create_loan_profile(opportunity, advisor, lead, property_address=None):
        return LoanProfileV1.objects.create(advisor=advisor,
                                            lead=lead,
                                            crm_object_type=LoanProfileV1.CRM_OBJECT_TYPE_CHOICES.opportunity,
                                            crm_id=opportunity['id'],
                                            crm_type=SALESFORCE_CRM_TYPE,
                                            new_property_address=property_address,
                                            **loan_profile_factory(opportunity))

    @staticmethod
    def _create_borrower(opportunity, loan_profile, borrower_address=None):
        return BorrowerV1.objects.create(loan_profile=loan_profile,
                                         mailing_address=borrower_address,
                                         **borrower_factory(opportunity))

    @staticmethod
    def _create_coborrower(opportunity, borrower):
        coborrower_data = coborrower_factory(opportunity)
        return (CoborrowerV1.objects.create(borrower=borrower, **coborrower_data)
                if coborrower_data
                else None)

    @staticmethod
    def _create_mortgage_profile(opportunity, loan_profile):
        mortgage_profile_data = mortgage_profile_factory(opportunity)
        mp_kind = mortgage_profile_data.get('kind')
        mp_class = {'Purchase': MortgageProfilePurchase,
                    'Refinance': MortgageProfileRefinance}.get(mp_kind)
        if mp_class is None:
            logger.warning('VENDOR-SF-API-BUILD-PROFILE-UNKNOWN-KIND %s', mp_kind)
            retval = None
        else:
            retval = mp_class.objects.create(loan_profilev1=loan_profile, **mortgage_profile_data)
        return retval


# pylint: disable=W0223
class MortgageProfileBearingBaseSerializer(serializers.Serializer):
    '''Serializes anything with a morgage_profile into a Salesforce Lead'''

    CONDO = 'Condo'
    HIGH_RISE_CONDO = 'High Rise Condominium'
    MULTI_UNIT = '2-4 Unit'

    unmapped_property_types = ['vacant_lot_land']

    # statics
    LeadSource = serializers.SerializerMethodField()
    Lead_Source_Details__c = serializers.SerializerMethodField()

    # ALIBI: hard-coded for now, will use this field to explain LP/RQT/PQ...
    Medium__c = serializers.SerializerMethodField()

    OwnerId = serializers.SerializerMethodField()

    # from Matt's code; confirmed necessary for routing
    Lead_Preferred_language__c = serializers.SerializerMethodField()
    Lead_Priority__c = serializers.SerializerMethodField()
    Pardot_Created__c = serializers.SerializerMethodField()

    Loan_Amount__c = serializers.SerializerMethodField()
    Loan_Balance__c = serializers.SerializerMethodField(
        allow_null=True, required=False, method_name='get_ExistingLiens__c')

    Loan_Purpose__c = serializers.CharField(source='mortgage_profile.kind', max_length=255,
                                            required=False)

    AdvisorEmail__c = serializers.CharField(
        source='mortgage_profile.advisor_email', allow_null=True, required=False)

    ARMComfort__c = serializers.SerializerMethodField(allow_null=True, required=False)

    Conversion_URL__c = serializers.URLField(
        source='mortgage_profile.conversion_url', allow_null=True, required=False, max_length=2000)
    ReferralURL__c = serializers.URLField(
        source='mortgage_profile.referral_url', allow_null=True, required=False, max_length=2000)

    Down_Payment_Amt__c = serializers.SerializerMethodField(allow_null=True, required=False)
    Estimated_Credit_Score_Range__c = serializers.CharField(
        source='mortgage_profile.credit_score', allow_null=True, required=False)

    ExistingLiens__c = serializers.SerializerMethodField(allow_null=True, required=False)
    Home_Ownership_Plan__c = serializers.CharField(
        source='morgage_profile.ownership_time', allow_null=True, required=False)

    Property_Type__c = serializers.SerializerMethodField(allow_null=True, required=False)
    Property_Use__c = serializers.SerializerMethodField(allow_null=True, required=False)
    Property_Value__c = serializers.SerializerMethodField(allow_null=True, required=False)

    RatePreference__c = serializers.CharField(
        source='mortgage_profile.rate_preference', allow_null=True, required=False)

    ReferrerEmail__c = serializers.CharField(
        source='mortgage_profile.referrer_email', allow_null=True, required=False)

    Refinance_Reason__c = serializers.SerializerMethodField(allow_null=True, required=False)

    sampleRateQuoteURL__c = serializers.SerializerMethodField(allow_null=True, required=False)

    # pylint: disable=R0201
    def get_ARMComfort__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            mp = obj.mortgage_profile
            if mp.adjustable_rate_comfort:
                return mp.ADJUSTABLE_RATE_CHOICES[mp.adjustable_rate_comfort]
        return None

    def get_Down_Payment_Amt__c(self, obj):
        if obj.mortgage_profile and self.context.get('typed_profile'):
            if hasattr(self.context['typed_profile'], 'purchase_down_payment'):
                return self.context['typed_profile'].purchase_down_payment
        return None

    def get_ExistingLiens__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            typed_profile = self.context.get('typed_profile')
            if typed_profile and hasattr(typed_profile, 'mortgage_owe'):
                return typed_profile.mortgage_owe
        return 0

    def get_LeadSource(self, obj):
        return self.context['LeadSource']

    def get_Lead_Source_Details__c(self, obj):
        return self.context['Lead_Source_Details__c']

    def get_Loan_Amount__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            typed_profile = self.context.get('typed_profile')
            if typed_profile:
                return typed_profile.get_loan_amount()
        return None

    def get_Lead_Preferred_language__c(self, obj):
        return self.context['Lead_Preferred_language__c']

    def get_Lead_Priority__c(self, obj):
        return self.context['Lead_Priority__c']

    def get_Medium__c(self, obj):
        return self.context['Medium__c']

    def get_OwnerId(self, obj):
        return self.context['OwnerId']

    def get_Pardot_Created__c(self, obj):
        return self.context['Pardot_Created__c']

    def get_Property_Type__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            if self.context.get('typed_profile'):
                typed_profile = self.context['typed_profile']
                if hasattr(typed_profile, 'property_type') and typed_profile.property_type:
                    if self.context['typed_profile'].property_type in self.unmapped_property_types:
                        return None
                    return {
                        MortgageProfile.PROPERTY_TYPE_CONDO_LESS_5: self.CONDO,
                        MortgageProfile.PROPERTY_TYPE_CONDOS_LIMITED: self.CONDO,
                        MortgageProfile.PROPERTY_TYPE_CONDOS_UNAPPROVED: self.CONDO,
                        MortgageProfile.PROPERTY_TYPE_CONDOTELS: self.CONDO,
                        MortgageProfile.PROPERTY_TYPE_CONDO__5_8: self.HIGH_RISE_CONDO,
                        MortgageProfile.PROPERTY_TYPE_CONDO_MORE_8: self.HIGH_RISE_CONDO,
                        MortgageProfile.PROPERTY_TYPE_MANUFACTURED_SINGLE: 'Manufactured Housing',
                        MortgageProfile.PROPERTY_TYPE_PUD_HAS_HOA_DUES: 'Planned Unit Development (PUD)',
                        MortgageProfile.PROPERTY_TYPE_SINGLE_FAMILY: 'Single Family Residence',
                        MortgageProfile.PROPERTY_TYPE_TOWNHOUSE: 'Townhome',
                        MortgageProfile.PROPERTY_TYPE_TWO_UNIT: self.MULTI_UNIT,
                        MortgageProfile.PROPERTY_TYPE_THREE_UNIT: self.MULTI_UNIT,
                        MortgageProfile.PROPERTY_TYPE_FOUR_UNIT: self.MULTI_UNIT
                    }[self.context['typed_profile'].property_type]
        return None

    def get_Property_Use__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            if obj.mortgage_profile.property_occupation:
                return {
                    # Purchase
                    MortgageProfilePurchase.FIRST_TIME_HOMEBUYER: 'Primary Home',
                    MortgageProfilePurchase.SELLING_HOME: 'Primary Home',
                    MortgageProfilePurchase.VACATION_HOME: 'Second Home',
                    MortgageProfilePurchase.INVESTMENT_PROPERTY: 'Investment Property',
                    # Refinance
                    MortgageProfile.PROPERTY_OCCUPATION_CHOICES.primary: 'Primary Home',
                    MortgageProfile.PROPERTY_OCCUPATION_CHOICES.secondary: 'Second Home',
                    MortgageProfile.PROPERTY_OCCUPATION_CHOICES.investment: 'Investment Property'
                }[obj.mortgage_profile.property_occupation]
            else:
                # TODO: remove once loansifter profiles are gone
                typed_profile = self.context['typed_profile']
                if hasattr(typed_profile, 'mismo_property_usage') and typed_profile.mismo_property_usage:
                    return LoanProfileV1.MISMO_PROPERTY_USAGE[typed_profile.mismo_property_usage]
        return None

    def get_Property_Value__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            if self.context.get('typed_profile'):
                return self.context['typed_profile'].get_property_value()
        return None

    def get_Refinance_Reason__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            subclass = obj.mortgage_profile.subclass
            return getattr(subclass, 'purpose', None)
        return None

    def get_sampleRateQuoteURL__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            rate_quote_request = obj.mortgage_profile.rate_quote_requests.first()
            if rate_quote_request:
                return "{0}/{1}/{2}".format(
                    get_consumer_portal_base_url(),
                    settings.CP_URL['VIEW_RATE_QUOTE'],
                    rate_quote_request.uuid)
        return None


# pylint: disable=W0223
class sampleContactRequestSerializer(MortgageProfileBearingBaseSerializer):
    '''Serializes sample ContactRequests as Salesforce leads'''

    FirstName = serializers.CharField(source='first_name', max_length=255)
    LastName = serializers.CharField(source='last_name', max_length=255)
    Email = serializers.EmailField(source='email', max_length=254, required=False)
    Phone = serializers.CharField(source='phone', max_length=255, required=False)

    Lead_State__c = serializers.SerializerMethodField()

    # ALIBI: Never populated in current RQT
    # Property_City__c = serializers.CharField(
    #    source='mortgage_profile.property_city', allow_null=False, required=False)

    Property_County__c = serializers.CharField(
        source='mortgage_profile.property_county', allow_null=True, required=False)

    Property_Zipcode__c = serializers.CharField(
        source='mortgage_profile.property_zipcode', allow_null=True, required=False)

    # pylint: disable=R0201
    def get_Lead_State__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            return settings.STATES_MAP.get(obj.mortgage_profile.property_state)
        return None


# pylint: disable=W0223
class sampleLoanProfileSerializer(MortgageProfileBearingBaseSerializer):
    '''Serializes sample LoanProfileV1s as Salesforce leads'''

    FirstName = serializers.CharField(source='primary_borrower.first_name', max_length=255)
    LastName = serializers.CharField(source='primary_borrower.last_name', max_length=255)
    Email = serializers.EmailField(source='primary_borrower.email', max_length=255, required=False)
    Phone = serializers.CharField(source='primary_borrower.home_phone', max_length=255, required=False)

    EmploymentStatus__c = serializers.SerializerMethodField()
    Marital_Status__c = serializers.CharField(source='primary_borrower.marital_status', max_length=255, required=False)
    Military_Service__c = serializers.NullBooleanField(source='primary_borrower.is_veteran')
    Citizenship__c = serializers.CharField(
        source='primary_borrower.citizenship_status', max_length=255, required=False)

    Coborrower__c = serializers.SerializerMethodField()
    CoborrowerName__c = serializers.CharField(source='primary_coborrower.full_name', max_length=255, required=False)

    Credit_Score__c = serializers.SerializerMethodField()
    DoNotCall = serializers.SerializerMethodField()
    HasOptedOutOfEmail = serializers.SerializerMethodField()
    Lead_Preferred_language__c = serializers.CharField(
        source='customer.get_preferred_language_display', max_length=255, default='English')

    Lead_State__c = serializers.SerializerMethodField()
    RealtorFullName__c = serializers.CharField(
        source='primary_borrower.realtor.username', max_length=255, required=False)

    RealtorEmail__c = serializers.CharField(source='primary_borrower.realtor.email', max_length=255, required=False)
    RealtorPhone__c = serializers.CharField(source='primary_borrower.realtor.phone', max_length=255, required=False)
    Property_City__c = serializers.CharField(source='subject_property_address.city', required=False)
    Property_Zipcode__c = serializers.SerializerMethodField()
    sampleID__c = serializers.CharField(source='guid', max_length=255, required=False)

    # pylint: disable=no-self-use
    def get_Coborrower__c(self, obj):
        if obj.other_on_loan == 'spouse_or_partner':
            return 'Spouse/Partner'
        elif obj.other_on_loan == 'no':
            return 'No'
        return None

    # pylint: disable=no-self-use
    def get_Credit_Score__c(self, obj):
        if getattr(obj, 'mortgage_profile', None):
            mp = obj.mortgage_profile
            if hasattr(mp, 'credit_score') and mp.credit_score:
                try:
                    num_score = int(mp.credit_score)
                    return num_score
                except ValueError:
                    return None
        return None

    # pylint: disable=R0201
    def get_DoNotCall(self, obj):
        if 'phone_ok' in obj.customer.contact_preferences:
            return not obj.customer.contact_preferences.get('phone_ok')
        return None

    # pylint: disable=no-self-use
    def get_EmploymentStatus__c(self, obj):
        return getattr(BorrowerBaseV1.JOB_STATUS_CHOICES, obj.primary_borrower.job_status, None)

    # pylint: disable=R0201
    def get_HasOptedOutOfEmail(self, obj):
        if 'email_ok' in obj.customer.contact_preferences:
            return not obj.customer.contact_preferences.get('email_ok')
        return None

    # pylint: disable=R0201
    def get_Lead_State__c(self, obj):
        if obj.subject_property_address:
            return obj.subject_property_address.state
        if getattr(obj, 'mortgage_profile', None):
            return settings.STATES_MAP.get(obj.mortgage_profile.property_state)
        return None

    # pylint: disable=R0201
    def get_Property_Zipcode__c(self, obj):
        if obj.subject_property_address:
            return obj.subject_property_address.postal_code
        if getattr(obj, 'mortgage_profile', None):
            return obj.mortgage_profile.property_zipcode

    # Items not yet supported in sample data model/Salesforce
    # x-Date of Pre-Qual success and status?
    # Pending Data Model
    # ContactPreference__c
