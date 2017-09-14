# -*- coding: utf-8 -*-
import logging

from django.conf import settings

from rest_framework import serializers

from contacts import models
from core.utils import get_state_code
from chat.models import Chat
from core import mixins
from pages.models import StateLicense

logger = logging.getLogger('sample.contacts.serializers')


class ContactRequestMortgageProfileSerializer(mixins.RecaptchaMixin, serializers.ModelSerializer):
    class Meta:
        model = models.ContactRequestMortgageProfile
        fields = ('first_name', 'last_name', 'email', 'phone', 'recaptcha_response')


class ConsultationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ConsultationRequest
        fields = (
            'first_name', 'last_name', 'phone', 'email', 'purchase_type', 'mortgage_timing', 'preferred_time',
            'mortgage_profile_kind')


class ContactRequestAboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContactRequestAboutUs
        fields = ('first_name', 'last_name', 'phone', 'email', 'message')


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Location
        fields = ('zipcode', 'county', 'state', 'city')


class ContactRequestPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContactRequestPartner
        fields = ('first_name', 'last_name', 'email',)


class ContactRequestLandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContactRequestLanding
        fields = (
            'first_name', 'last_name', 'phone', 'email', 'purchase_type', 'mortgage_timing', 'preferred_time',
            'mortgage_profile_kind')


class ContactRequestLandingExtendedSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContactRequestLandingExtended
        fields = (
            'first_name', 'last_name', 'phone', 'email', 'mortgage_profile_kind', 'property_zipcode',
            'property_state', 'property_county', 'is_veteran', 'credit_rating', 'ownership_time', 'purchase_timing',
            'annual_income_amount', 'monthly_debt',
            'purchase_type', 'purchase_property_value', 'purchase_down_payment', 'refinance_purpose',
            'refinance_property_value', 'refinance_mortgage_balance',
        )


class WritableJSONField(serializers.Field):
    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


def steps_progress_default():
    current_chat = Chat.objects.first()
    if current_chat:
        return {guid: {'completed': False} for guid in current_chat.steps_guids}
    else:
        return {}


class ContactRequestMobileProfileSerializer(serializers.ModelSerializer):
    steps_progress = WritableJSONField(default=steps_progress_default)

    class Meta:
        model = models.ContactRequestMobileProfile
        fields = (
            'first_name', 'last_name', 'credit_rating', 'annual_income_amount', 'monthly_housing_expense',
            'monthly_nonhousing_expense', 'down_payment_amount', 'email', 'phone',
            'mortgage_profile', 'steps_progress',
        )


class ContactRequestUnlicensedStateSerializer(mixins.RecaptchaMixin, serializers.ModelSerializer):
    first_name = serializers.CharField(allow_blank=False, allow_null=False, max_length=255, required=True)
    last_name = serializers.CharField(allow_blank=False, allow_null=False, max_length=255, required=True)
    unlicensed_state_code = serializers.ChoiceField(
        allow_blank=False, allow_null=False, required=True, choices=settings.STATE_CODES)

    # pylint: disable=no-self-use
    def validate_unlicensed_state_code(self, unlicensed_state_code):
        licensed_state_codes = {get_state_code(license.state_name) for license in StateLicense.objects.all()}
        if unlicensed_state_code in licensed_state_codes:
            logger.error(
                'CONTACT-REQUEST-UNLICENSED-STATE-FOR-STATE-WITH-LICENSE unlicensed_state_code %s',
                unlicensed_state_code)
        return unlicensed_state_code

    class Meta:
        model = models.ContactRequestUnlicensedState
        fields = ('first_name', 'last_name', 'email', 'phone', 'unlicensed_state_code', 'recaptcha_response')
