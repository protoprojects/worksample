# -*- coding: utf-8 -*-
from decimal import Decimal
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.utils import memoize

from mortgage_profiles.models import (
    MortgageProfile, MortgageProfilePurchase, MortgageProfileRefinance,
    RateQuoteLender
)


class RateQuoteValidator(object):
    """
    validates:
        (1) this is for an existing mortgage_profile
        (2) that a rate_quote_lender can only be related to a mortgage_profile that was used
            to generate the rate quote request
        (3) the relationship between a rate_quote_lender and mortgage_profile is one-to-one
    """

    def set_context(self, serializer_field):
        """This hook is called by the serializer instance, prior to the validation call being made."""
        # Determine the existing instance, if this is an update operation.
        # pylint: disable=attribute-defined-outside-init
        self.mortgage_profile = getattr(serializer_field.parent, 'instance', None)

    @staticmethod
    def validate_mortgage_profile_exists(mortgage_profile):
        # if the mortgage_profile does not exist, then this a .create operation
        # instead of an .update operation.
        if mortgage_profile is None:
            raise serializers.ValidationError('cannot set this field on create')

    @staticmethod
    def validate_already_related(mortgage_profile, rate_quote_lender):
        if rate_quote_lender.request.mortgage_profile.id != mortgage_profile.id:
            # ALIBI: this mirrors the error message for a non-existing rate_quote_lender.id
            # to avoid leaking information about existing rate_quote_lender objects to users who
            # are note associated with the rate_quote_lender object
            raise serializers.ValidationError('Invalid pk "{0}" - object does not exist.'.format(rate_quote_lender.id))

    @staticmethod
    def validate_one_to_one(mortgage_profile, rate_quote_lender):
        queryset = MortgageProfile.objects.filter(
            selected_rate_quote_lender=rate_quote_lender).exclude(pk=mortgage_profile.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                'This field must be unique.  '
                'Another mortgage_profile already references this rate_quote_lender.')

    def __call__(self, rate_quote_lender):
        self.validate_mortgage_profile_exists(self.mortgage_profile)
        self.validate_already_related(self.mortgage_profile, rate_quote_lender)
        self.validate_one_to_one(self.mortgage_profile, rate_quote_lender)


######################
# lender serializers #
######################
class RateQuoteLenderSerializer(serializers.ModelSerializer):
    points = serializers.SerializerMethodField('get_custom_full_points')
    apr = serializers.SerializerMethodField('get_custom_apr')
    total_monthly_payment = serializers.SerializerMethodField('get_custom_total_monthly_payment')
    monthly_payment = serializers.SerializerMethodField('get_custom_monthly_payment')
    fees = serializers.SerializerMethodField('get_custom_fees')
    total_fees = serializers.SerializerMethodField('get_custom_total_fees')
    rate_percent = serializers.SerializerMethodField()

    class Meta:
        model = RateQuoteLender
        fields = (
            'id', 'lender_name', 'amortization_type', 'term', 'program_type', 'program_name', 'points', 'rate', 'apr',
            'fees', 'total_monthly_payment', 'total_fees', 'monthly_payment', 'rate_percent', 'mismo_amortization_type',
            'mismo_fnm_product_plan_identifier', 'created', 'qualifying_rate', 'is_variable', 'is_fixed')

    # pylint: disable=no-self-use
    @memoize
    def get_calculations(self, lender, lender_id):
        ''' Used by methods below to fetch calculations from fees.py. '''
        # lender_id is here only for hacking memoize decorator
        from mortgage_profiles.mortech.fees import MortechFees
        return MortechFees(lender.request.mortgage_profile.subclass, lender)

    # pylint: disable=no-self-use
    def get_custom_full_points(self, lender):
        if lender.id:
            return lender.points

    def get_custom_apr(self, lender):
        ''' Return custom Annual Percentage Rate (APR). '''
        if lender.id:
            return lender.apr

    def get_custom_monthly_payment(self, lender):
        if lender.id:
            return lender.monthly_payment

    def get_custom_total_monthly_payment(self, lender):
        if lender.id:
            return self.get_calculations(lender, lender.id).get_total_monthly_payment()

    def get_custom_fees(self, lender):
        '''TODO: Configure any custom fees.'''
        if lender.id:
            return self.get_calculations(lender, lender.id).get_non_zero_fees()

    def get_custom_total_fees(self, lender):
        if lender.id:
            return self.get_calculations(lender, lender.id).get_total_fees()

    def get_rate_percent(self, lender):
        '''Convert the rate in basis points to percentage points

        example: lender.rate of 412.5 becomes 4.125

        '''
        if lender.id:
            return Decimal(lender.rate) / Decimal(100.0)


################################
# mortgage profile serializers #
################################
class MortgageProfilePurchaseSerializer(serializers.ModelSerializer):
    """
    selected_lender_id represents the rate_quote_lender.id selected by the customer for their application.
    if the customer does not actively select a lender, then this field is populated based on sample’s recommendation

    selected_lender is a read_only serialized representation of the rate_quote_lender whose id is in selected_lender_id

    note: having the selected_lender_id be a read/write field and selected_lender be read only field works more
          easily in django rest_framework than trying to have a selected_lender handle reads and writes, which would
          require either nested url endpoints or writing custom .update methods for this serializer

    """
    selected_lender_id = serializers.PrimaryKeyRelatedField(
        source='selected_rate_quote_lender',
        allow_null=True,
        queryset=RateQuoteLender.objects.all(),
        required=False,
        validators=[RateQuoteValidator()])
    selected_lender = RateQuoteLenderSerializer(source='selected_rate_quote_lender', required=False, read_only=True)
    is_veteran = serializers.NullBooleanField(required=False)
    id = serializers.UUIDField(source='uuid', required=False, read_only=True)
    # Default values for external POST requests to rate quote view
    # Eventually we'll want custom serializers to handle external requests in v2
    ownership_time = serializers.CharField(default='not_sure')
    property_type = serializers.CharField(default='single_family')

    class Meta:
        model = MortgageProfilePurchase
        fields = (
            'id', 'kind', 'adjustable_rate_comfort', 'purchase_timing', 'purchase_down_payment', 'purchase_type',
            'ownership_time', 'property_type', 'property_state', 'property_county', 'property_zipcode',
            'target_value', 'is_veteran', 'hoa_dues', 'rate_preference', 'credit_score',
            'advisor_email', 'referrer_email', 'referral_url', 'conversion_url', 'property_occupation',
            'selected_lender_id', 'selected_lender'
        )


class MortgageProfileRefinanceSerializer(serializers.ModelSerializer):
    """
    see MortgageProfilePurchaseSerializer docstring for info on:
     - selected_lender
     - selected_lender_id
    """
    selected_lender_id = serializers.PrimaryKeyRelatedField(
        source='selected_rate_quote_lender',
        allow_null=True,
        queryset=RateQuoteLender.objects.all(),
        required=False,
        validators=[RateQuoteValidator()])
    selected_lender = RateQuoteLenderSerializer(source='selected_rate_quote_lender', required=False, read_only=True)
    is_veteran = serializers.NullBooleanField(required=False)
    id = serializers.UUIDField(source='uuid', required=False, read_only=True)
    # Default values for external POST requests to rate quote view
    # Eventually we'll want custom serializers to handle external requests in v2
    ownership_time = serializers.CharField(default='not_sure')
    property_type = serializers.CharField(default='single_family')

    class Meta:
        model = MortgageProfileRefinance
        fields = (
            'id', 'kind', 'purpose', 'property_state', 'property_zipcode', 'property_county', 'property_type',
            'mortgage_owe', 'property_value', 'property_occupation', 'mortgage_term', 'mortgage_start_date',
            'mortgage_monthly_payment', 'is_veteran', 'cashout_amount', 'ownership_time', 'hoa_dues',
            'adjustable_rate_comfort', 'rate_preference', 'credit_score', 'advisor_email', 'referrer_email',
            'referral_url', 'conversion_url', 'selected_lender_id', 'selected_lender'
        )


class MortgageProfileSerializer(serializers.ModelSerializer):
    """
    Can be used solely as read_only

    For doing polymorphic .updates instead overwrite the .get_serializer method in the view.
    see customer_portal.views.mortgage_profile.MortgageProfileView for an example
    """
    id = serializers.UUIDField(source='uuid', required=False, read_only=True)

    class Meta:
        model = MortgageProfile
        fields = '__all__'

    def to_representation(self, obj):
        """
        polymorphic return
        """
        if isinstance(obj, MortgageProfilePurchase):
            return MortgageProfilePurchaseSerializer(obj, context=self.context).to_representation(obj)
        elif isinstance(obj, MortgageProfileRefinance):
            return MortgageProfileRefinanceSerializer(obj, context=self.context).to_representation(obj)
        raise ValidationError('unexpected mortgage_profile type')
