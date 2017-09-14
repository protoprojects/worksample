# -*- coding: utf-8 -*-
import logging
import re

from functools import partial

from django.db import models
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.core.validators import MinValueValidator, MaxValueValidator

from model_utils import Choices
from model_utils.managers import InheritanceManager
import encrypted_fields
from shortuuidfield import ShortUUIDField

from contacts.models import Location
from core.models import TimeStampedModel, EncryptedNullBooleanField, EncryptedDataField
from core.utils import create_shortuuid, get_state_code, as_currency
from accounts.models import User
from loans.models import LoanProfileV1, DEFAULT_CURRENCY
from money.models.fields import MoneyField

from core.validators import MyMaxValueValidator, MyMinValueValidator


logger = logging.getLogger("sample.mortgage_profiles")

zip_re = re.compile(r'^\d{5}$')


class MortgageProfile(TimeStampedModel):
    """
    Parent model for different mortgage profiles.

    Each child shoud contain ``MORTGAGE_PROFILE_KIND``.

    """
    REFINANCE = "refinance"
    PURCHASE = "purchase"
    KINDS = (
        (REFINANCE, "Refinance"),
        (PURCHASE, "Purchase")
    )

    sample_TO_MISMO_MORTGAGE_KIND = {
        REFINANCE: 'Refinance',
        PURCHASE: 'Purchase',
    }

    MISMO_TO_sample_MORTGAGE_KIND = {value: key for key, value in sample_TO_MISMO_MORTGAGE_KIND.items()}

    ADJUSTABLE_RATE_CHOICES = Choices(('yes', 'Yes'), ('no', 'No'), ('unsure', 'Not Sure'))
    RATE_PREFERENCE_CHOICES = Choices(('fixed', 'Fixed'), ('variable', 'Variable'))

    LONG_TERM = 'long_term'
    MEDIUM_TERM = 'medium_term'
    SHORT_TERM = 'short_term'
    NOT_SURE = 'not_sure'
    OWNERSHIP_TIME_CHOICES = (
        (LONG_TERM, "Long term / Quite a while"),
        (MEDIUM_TERM, "Medium term  / 5-15 years"),
        (SHORT_TERM, "Short term / Only a few years"),
        (NOT_SURE, "Not Sure")
    )
    # Implemented on rate quote tool
    PROPERTY_TYPE_SINGLE_FAMILY = 'single_family'
    PROPERTY_TYPE_CONDO_LESS_5 = 'condo_less_5'
    PROPERTY_TYPE_CONDO__5_8 = 'condo_5_8'
    PROPERTY_TYPE_CONDO_MORE_8 = 'condo_more_8'
    PROPERTY_TYPE_TOWNHOUSE = 'townhouse'
    PROPERTY_TYPE_TWO_UNIT = 'two_unit'
    PROPERTY_TYPE_THREE_UNIT = 'three_unit'
    PROPERTY_TYPE_FOUR_UNIT = 'four_unit'
    # Loansifter Only
    PROPERTY_TYPE_CONDOS_LIMITED = 'condo_limited'
    PROPERTY_TYPE_CONDOS_UNAPPROVED = 'condo_unapproved'
    PROPERTY_TYPE_CONDOTELS = 'condotel'
    PROPERTY_TYPE_PUD_HAS_HOA_DUES = 'pud_has_hoa_dues'  # "Planned Unit Development" development plan for a large area
    PROPERTY_TYPE_VACANT_LOT_LAND = 'vacant_lot_land'
    # Not implemented on rate quote tool
    PROPERTY_TYPE_UNWARRANTED_CONDOS_LOW = 'condo_unwarranted_less_5'
    PROPERTY_TYPE_UNWARRANTED_CONDOS_MID = 'condo_unwarranted_5_8'
    PROPERTY_TYPE_UNWARRANTED_CONDOS_HIGH = 'condo_unwarranted_more_8'
    PROPERTY_TYPE_CONDOTEL_LOW = 'condotel_low'
    PROPERTY_TYPE_CONDOTEL_MID = 'condotel_mid'
    PROPERTY_TYPE_CONDOTEL_HIGH = 'condotel_high'
    PROPERTY_TYPE_MANUFACTURED_SINGLE = 'manufactured_single'
    PROPERTY_TYPE_CHOICES = (
        (PROPERTY_TYPE_SINGLE_FAMILY, 'Single family residence'),
        (PROPERTY_TYPE_CONDO_LESS_5, 'Condo (<5 stories)'),
        (PROPERTY_TYPE_CONDO__5_8, 'Condo (5-8 stories)'),
        (PROPERTY_TYPE_CONDO_MORE_8, 'Condo (>8 stories)'),
        (PROPERTY_TYPE_TOWNHOUSE, 'Townhouse'),
        (PROPERTY_TYPE_TWO_UNIT, 'Two-unit'),
        (PROPERTY_TYPE_THREE_UNIT, 'Three-unit'),
        (PROPERTY_TYPE_FOUR_UNIT, 'Four-unit'),
        (PROPERTY_TYPE_MANUFACTURED_SINGLE, 'Manufactured singlewide'),
        # Loansifter Only
        (PROPERTY_TYPE_VACANT_LOT_LAND, 'Vacant Lot/Land'),
        (PROPERTY_TYPE_PUD_HAS_HOA_DUES, 'PUD/Has HOA dues'),
    )

    sample_TO_MISMO_PROPERTY_TYPE = {  # GSEPropertyType NOT _GSEPropertyType
        # commented out values are valid MISMO but not mapped...
        PROPERTY_TYPE_TOWNHOUSE: 'Attached',
        PROPERTY_TYPE_CONDO_LESS_5: 'Condominium',
        # 'Cooperative',
        PROPERTY_TYPE_SINGLE_FAMILY: 'Detached',
        PROPERTY_TYPE_TWO_UNIT: 'Detached',  # ok to duplicate "Attached", needed for consumer portal
        # 'DetachedCondominium',
        # 'HighRiseCondominium',
        # 'MHSelect',
        # 'ManufacturedHousing',
        PROPERTY_TYPE_MANUFACTURED_SINGLE: 'ManufacturedHousingSingleWide',
        # 'ManufacturedHousingMultiWide',
        # 'ManufacturedHousingDoubleWide',
        # 'Modular',
        # 'ManufacturedHomeCondominium',
        # 'ManufacturedHomeCondominiumOrPUDOrCooperative',
        PROPERTY_TYPE_PUD_HAS_HOA_DUES: 'PUD',
    }

    MISMO_TO_sample_PROPERTY_TYPE = {value: key for key, value in sample_TO_MISMO_PROPERTY_TYPE.items()}

    # Consumer portal rate quote tool refresh status
    REFRESH_PROGRESS_CHOICES = Choices(
        ('in_progress', 'In Progress'),
        ('complete', 'Complete')
    )

    PROPERTY_OCCUPATION_CHOICES = Choices(
        ('my_current_residence', 'primary', 'My Current Residence'),
        ('second_home_vacation_home', 'secondary', 'Second Home/Vacation Home'),
        ('investment_property', 'investment', 'Investment Property'),
    )

    sample_TO_MISMO_PROPERTY_USAGE = {
        PROPERTY_OCCUPATION_CHOICES.primary: LoanProfileV1.MISMO_PROPERTY_USAGE.PrimaryResidence,
        PROPERTY_OCCUPATION_CHOICES.secondary: LoanProfileV1.MISMO_PROPERTY_USAGE.SecondHome,
        PROPERTY_OCCUPATION_CHOICES.investment: LoanProfileV1.MISMO_PROPERTY_USAGE.Investor
    }

    MISMO_TO_sample_PROPERTY_OCCUPATION = {value: key for key, value in sample_TO_MISMO_PROPERTY_USAGE.items()}

    # Related Objects
    uuid = ShortUUIDField(max_length=22, default=partial(create_shortuuid), unique=True, blank=True, editable=False)
    user = models.ForeignKey(User, related_name="mortgage_profiles", blank=True, null=True)
    loan_profilev1 = models.ForeignKey(LoanProfileV1, related_name="mortgage_profiles", blank=True, null=True)
    selected_rate_quote_lender = models.OneToOneField('RateQuoteLender',
                                                      on_delete=models.SET_NULL,
                                                      related_name='mortgage_profile',
                                                      blank=True, null=True)

    kind = models.CharField(max_length=255, choices=KINDS)
    advisor_email = models.EmailField(max_length=255, blank=True)
    adjustable_rate_comfort = models.CharField(max_length=255, blank=True, choices=ADJUSTABLE_RATE_CHOICES)
    rate_preference = models.CharField(max_length=255, blank=True, choices=RATE_PREFERENCE_CHOICES)
    referrer_email = models.EmailField(max_length=255, blank=True)
    referral_url = models.TextField(blank=True)
    conversion_url = models.TextField(blank=True)

    ownership_time = encrypted_fields.EncryptedCharField(max_length=255, blank=True, choices=OWNERSHIP_TIME_CHOICES)
    # we do not collect HOA dues in the RateQuote.  HOA does for the customer_portal are collected in
    # loan_profile.borrowers.first().expense.filter(kind=ExpenseV1.HOA)
    hoa_dues = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                          max_digits=10, decimal_places=2, default=None)
    # Support for frontend consumer portal work. Credit rating ranges going away at launch.
    # Specific scores will be used going thereafter. XXXkayhudson
    max_value = 850
    min_value = 0
    credit_score = models.IntegerField(
        null=True, blank=True,
        validators=[
            MyMinValueValidator(
                min_value,
                message='Credit score must be greater than {}.'.format(min_value)),
            MyMaxValueValidator(
                max_value,
                message='Credit score must be less than {}.'.format(max_value))])
    is_veteran = EncryptedNullBooleanField()
    property_zipcode = encrypted_fields.EncryptedCharField(max_length=255, blank=True)
    property_state = encrypted_fields.EncryptedCharField(max_length=255, blank=True)
    property_city = encrypted_fields.EncryptedCharField(max_length=255, blank=True)
    property_county = encrypted_fields.EncryptedCharField(max_length=255, blank=True)
    property_type = encrypted_fields.EncryptedCharField(max_length=255,
                                                        blank=True, choices=PROPERTY_TYPE_CHOICES)
    property_occupation = encrypted_fields.EncryptedCharField(max_length=255, blank=True)

    rate_quote_refresh_progress = models.CharField(max_length=255, blank=True, choices=REFRESH_PROGRESS_CHOICES)

    @property
    def property_state_code(self):
        return get_state_code(self.property_state) or 'CA'

    objects = InheritanceManager()

    class Meta:
        ordering = ("-created",)
        verbose_name = "Mortgage profile"
        verbose_name_plural = "All mortgage profiles"
        app_label = 'mortgage_profiles'

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"{} mortgage profile".format(self.get_kind_display())

    def save(self, *args, **kwargs):
        # TODO: remove kind field from model
        if not self.kind or (hasattr(self, 'MORTGAGE_PROFILE_KIND') and self.kind != self.MORTGAGE_PROFILE_KIND):
            self.kind = self.MORTGAGE_PROFILE_KIND
        if self.property_county and not self.property_zipcode:
            loc = Location.objects.filter(county=self.property_county).first()
            if loc and zip_re.match(loc.zipcode):
                self.property_zipcode = loc.zipcode
        return super(MortgageProfile, self).save(*args, **kwargs)

    def get_loan_amount(self):
        raise NotImplementedError

    def get_property_value(self):
        raise NotImplementedError

    def is_va_loan_suitable(self):
        raise NotImplementedError

    def get_loan_to_value(self):
        return float(self.get_loan_amount()) / self.get_property_value()

    def is_loan_to_value_less_than(self, percent):
        return self.get_loan_to_value() <= percent

    def get_mortgage_purpose(self):
        raise NotImplementedError

    def get_type_of_purchase(self):
        raise NotImplementedError

    def get_property_type(self):
        return self.get_property_type_display()

    def get_property_location(self):
        location = '{}, {}'.format(self.property_county, self.property_state)
        return location

    def update_refresh_status(self, status):
        """Set the rate quote progress status."""
        self.rate_quote_refresh_progress = status

    def current_rate_quote_request(self):
        return self.rate_quote_requests.order_by('-created').first()

    def update_selected_lender(self):
        """Update rate quote lender when new results are requested."""
        request = self.current_rate_quote_request()
        if self.selected_rate_quote_lender and request.has_lenders:
            term, amortization = self.selected_rate_quote_lender.term, self.selected_rate_quote_lender.amortization_type
            if request.has_lender_product(term, amortization):
                # get par rate
                lender = request.get_rate_quote(term, amortization)
                # check if there is a discounted loan at that rate
                new_selected_lender = request.get_rate_quote(term, amortization, lender.rate)
                # Not sure we need the following check; method is only for when a new request is made. XXXkayhudson
                if new_selected_lender is self.selected_rate_quote_lender:
                    logger.error('SELECTED-LENDER-FAILED-TO-UPDATE mortgage_profile %s lender %s',
                                 self.id, self.selected_rate_quote_lender)
                else:
                    logger.debug('SELECTED-LENDER-UPDATED mortgage_profile %s old %s new %s',
                                 self.id, self.selected_rate_quote_lender, new_selected_lender)
                self.selected_rate_quote_lender = new_selected_lender
                self.save()
                return new_selected_lender
        else:
            logger.debug('SELECTED-LENDER-NOT-UPDATED mortgage_profile %s', self.id)
            return None

    @property
    def property_county_name(self):
        return (self.property_county.replace('County', '').strip()
                if self.property_county
                else '')

    @property
    def is_purchase(self):
        return self.kind == self.PURCHASE

    @property
    def is_refinance(self):
        return self.kind == self.REFINANCE

    @property
    def subclass(self):
        return MortgageProfile.objects.get_subclass(id=self.id)

    def mismo_kind(self):
        return self.sample_TO_MISMO_MORTGAGE_KIND.get(self.kind)

    # mismo GSEPropertyType NOT _GSEPropertyType
    def mismo_property_type(self):
        return self.sample_TO_MISMO_PROPERTY_TYPE.get(self.property_type)

    # mismo _FinancedNumberOfUnits
    def mismo_FinancedNumberOfUnits(self):
        return {
            self.PROPERTY_TYPE_SINGLE_FAMILY: 1,
            self.PROPERTY_TYPE_CONDO_LESS_5: 1,
            self.PROPERTY_TYPE_CONDO__5_8: 1,
            self.PROPERTY_TYPE_CONDO_MORE_8: 1,
            self.PROPERTY_TYPE_TOWNHOUSE: 1,
            self.PROPERTY_TYPE_TWO_UNIT: 2,
            self.PROPERTY_TYPE_THREE_UNIT: 3,
            self.PROPERTY_TYPE_FOUR_UNIT: 4,
            self.PROPERTY_TYPE_MANUFACTURED_SINGLE: 1,
            self.PROPERTY_TYPE_PUD_HAS_HOA_DUES: 1,
            self.PROPERTY_TYPE_VACANT_LOT_LAND: 0,
        }[self.property_type]

    @classmethod
    def mismo_to_sample_kind(cls, kind):
        return cls.MISMO_TO_sample_MORTGAGE_KIND.get(kind)

    @classmethod
    def mismo_to_sample_property_type(cls, property_type):
        return cls.MISMO_TO_sample_PROPERTY_TYPE.get(property_type, 'detached')

    @staticmethod
    @receiver(user_logged_in, dispatch_uid="attach_mortgage_profile_to_user")
    def attach_mortgage_profile(sender, user, request, **kwargs):
        """
        Attach mortgage profile to logged in user.

        Workflow:
        1. Created mortgage profile.
        2. Logged in to account.
        3. Assigned mortgage profile to logged in account.

        """
        if request.user.is_customer() and request.session.get('mortgage_profile_uuid'):
            mortgage_profile = MortgageProfile.objects.get(uuid=request.session['mortgage_profile_uuid'])
            request.user.mortgage_profiles.add(mortgage_profile)

            logger.info(u'Mortgage profile %s attached to user %s',
                        mortgage_profile.id, request.user)

    @property
    def mismo_property_usage(self):
        return self.sample_TO_MISMO_PROPERTY_USAGE.get(self.property_occupation)

    @classmethod
    def mismo_to_sample_property_occupation(cls, occupation):
        return cls.MISMO_TO_sample_PROPERTY_OCCUPATION.get(occupation)

    @property
    def is_second_home_or_investment(self):
        return self.mismo_property_usage in (LoanProfileV1.MISMO_PROPERTY_USAGE.Investor,
                                             LoanProfileV1.MISMO_PROPERTY_USAGE.SecondHome)

    def is_primary_residence(self):
        return self.mismo_property_usage == LoanProfileV1.MISMO_PROPERTY_USAGE.PrimaryResidence

    def is_cash_out(self):
        # pylint: disable=no-self-use
        return False


class MortgageProfilePurchase(MortgageProfile):
    """
    Model for purchase mortgage profiles. This property customer wants to buy.

    """
    MORTGAGE_PROFILE_KIND = MortgageProfile.PURCHASE

    FIRST_TIME_HOMEBUYER = 'first_time_homebuyer'
    SELLING_HOME = 'selling_home'
    VACATION_HOME = 'vacation_home'
    INVESTMENT_PROPERTY = 'investment_property'
    PURCHASE_TYPE_CHOICES = (
        (FIRST_TIME_HOMEBUYER, 'First Time Homebuyer'),
        (SELLING_HOME, 'Selling Home/Moving'),
        (VACATION_HOME, 'Second Home/Vacation Home'),
        (INVESTMENT_PROPERTY, 'Investment Property'),
    )

    DEFAULT_PURCHASE_TYPE = SELLING_HOME

    MISMO_TO_sample_PURCHASE_TYPE = {
        LoanProfileV1.MISMO_PROPERTY_USAGE.PrimaryResidence: SELLING_HOME,
        LoanProfileV1.MISMO_PROPERTY_USAGE.SecondHome: VACATION_HOME,
        LoanProfileV1.MISMO_PROPERTY_USAGE.Investor: INVESTMENT_PROPERTY
    }

    RESEARCHING_OPTIONS = 'researching_options'
    BUYING_IN_3_MONTHS = 'buying_in_3_months'
    OFFER_SUBMITTED = 'offer_submitted'
    CONTRACT_IN_HAND = 'contract_in_hand'
    PURCHASE_TIMING_CHOICES = (
        (RESEARCHING_OPTIONS, 'Not sure / just researching'),
        (BUYING_IN_3_MONTHS, 'Buying in the next 3 months'),
        (OFFER_SUBMITTED, 'House in mind / offer submitted'),
        (CONTRACT_IN_HAND, 'Purchase contract in hand')
    )

    max_value = 10000000
    min_value = 10000
    purchase_timing = encrypted_fields.EncryptedCharField(max_length=255, blank=True, choices=PURCHASE_TIMING_CHOICES)
    # purchase_type is used by legacy rate quote only.  Conumser portal uses property_occupation
    purchase_type = encrypted_fields.EncryptedCharField(max_length=255, blank=True, choices=PURCHASE_TYPE_CHOICES)
    purchase_down_payment = encrypted_fields.EncryptedIntegerField(
        blank=True, null=True,
        validators=[
            MyMaxValueValidator(
                max_value,
                message='Down payment must be less than {}.'.format(as_currency(max_value)))])
    target_value = encrypted_fields.EncryptedIntegerField(
        blank=True, null=True,
        validators=[
            MyMinValueValidator(
                min_value,
                message='Purchase price must be greater than {}.'.format(as_currency(min_value))),
            MyMaxValueValidator(
                max_value,
                message='Purchase price must be less than {}.'.format(as_currency(max_value)))])

    class Meta(MortgageProfile.Meta):
        verbose_name = "Purchase mortgage profile"
        verbose_name_plural = "Purchase mortgage profiles"
        app_label = 'mortgage_profiles'

    @models.permalink
    def get_admin_link(self):
        return "admin:mortgage_profiles_mortgageprofilepurchase_change", (self.id,)

    def get_loan_amount(self):
        """Return difference between target value and down payment"""
        assert self.target_value, 'self.target_value should be defined'
        assert self.purchase_down_payment is not None, 'self.purchase_down_payment is None'

        result = self.target_value - self.purchase_down_payment
        logger.debug(u'MP-LOAN-AMOUNT %s profile %s user %s',
                     result, self.get_kind_display(), self.user)
        return result

    def get_property_value(self):
        """Return property value"""
        assert self.target_value, 'self.target_value should be defined'

        result = self.target_value
        logger.debug(u'MP-PROPERTY-VALUE %s profile %s user %s',
                     result, self.get_kind_display(), self.user)
        return result

    def is_va_loan_suitable(self):
        """Return whether VA loans are suitable for current mortgage profile"""
        assert self.purchase_type, 'self.purchase_type should be defined'

        return self.purchase_type in (self.FIRST_TIME_HOMEBUYER, self.SELLING_HOME)

    def get_mortgage_purpose(self):
        return self.get_purchase_timing_display()

    def get_type_of_purchase(self):
        return self.get_purchase_type_display()


class MortgageProfileRefinance(MortgageProfile):
    """Model for refinance mortgage profiles. This property customer own"""
    MORTGAGE_PROFILE_KIND = MortgageProfile.REFINANCE

    # Loan purpose
    LOWER_MORTGAGE_PAYMENTS = 'lower_mortgage_payments'
    CASH_OUT = 'cash_out'
    HELOC = 'heloc'
    BOTH = 'both'
    PURPOSE_CHOICES = (
        (LOWER_MORTGAGE_PAYMENTS, 'Lower mortgage rate or payment'),
        (CASH_OUT, 'Tap into equity/cash out'),
        (HELOC, 'Home equity line of credit'),
        (BOTH, 'Both'),
    )

    sample_TO_MISMO_REFINANCE_PURPOSE = {
        CASH_OUT: 'CashOutOther',
        LOWER_MORTGAGE_PAYMENTS: 'CashOutLimited'
    }

    MISMO_TO_sample_REFINANCE_PURPOSE = {value: key for key, value in sample_TO_MISMO_REFINANCE_PURPOSE.items()}

    MORTGAGE_TERM_CHOICES = (
        ('40_year', '40 Year'),
        ('30_year', '30 Year'),
        ('20_year', '20 Year'),
        ('15_year', '15 Year'),
        ('10_year', '10 Year')
    )

    max_value = 10000000
    min_value = 10000
    purpose = encrypted_fields.EncryptedCharField(max_length=255, blank=True, choices=PURPOSE_CHOICES)
    property_value = encrypted_fields.EncryptedIntegerField(
        blank=True, null=True,
        validators=[
            MyMinValueValidator(
                min_value,
                message='Property value must be greater than {}.'.format(as_currency(min_value))),
            MyMaxValueValidator(
                max_value,
                message='Property value must be less than {}.'.format(as_currency(max_value)))])
    mortgage_owe = encrypted_fields.EncryptedIntegerField(
        blank=True, null=True,
        validators=[
            MyMaxValueValidator(
                max_value,
                message='Current mortgage balance must be less than {}.'.format(as_currency(max_value)))])


    mortgage_term = encrypted_fields.EncryptedCharField(max_length=255, blank=True, choices=MORTGAGE_TERM_CHOICES)
    mortgage_start_date = EncryptedDataField(blank=True, null=True)
    mortgage_rate = encrypted_fields.EncryptedIntegerField(blank=True, null=True)
    mortgage_monthly_payment = encrypted_fields.EncryptedIntegerField(blank=True, null=True)

    cashout_amount = encrypted_fields.EncryptedIntegerField(blank=True, null=True)

    class Meta(MortgageProfile.Meta):
        verbose_name = "Refinance mortgage profile"
        verbose_name_plural = "Refinance mortgage profiles"
        app_label = 'mortgage_profiles'

    @models.permalink
    def get_admin_link(self):
        return "admin:mortgage_profiles_mortgageprofilerefinance_change", (self.id,)

    def get_loan_amount(self):
        assert self.mortgage_owe is not None, "self.mortgage_owe is None"

        result = self.mortgage_owe

        if (self.purpose == MortgageProfileRefinance.CASH_OUT) and self.cashout_amount:
            result += self.cashout_amount
        logger.debug(u"Loan amount: %s for Profile: %s, User: %s.",
                     result, self.get_kind_display(), self.user)
        return result

    def get_property_value(self):
        assert self.property_value, "self.property_value should be defined"

        result = self.property_value
        logger.debug(u"Property value: %s for Profile: %s, User: %s.",
                     result, self.get_kind_display(), self.user)
        return result

    def is_va_loan_suitable(self):
        """
        Return bool that represent if VA loans suitable for current mortgage profile.

        """
        assert self.property_occupation, "self.property_occupation should be defined"

        return self.property_occupation == self.PROPERTY_OCCUPATION_CHOICES.primary

    def get_mortgage_purpose(self):
        return self.get_purpose_display()

    def get_type_of_purchase(self):
        return self.get_property_occupation_display()

    def get_loan_profile_purpose_of_refi(self):
        """maps the MortgageProfileRefinance.purpose to a LoanProfileV1.purpose_of_refinance"""
        return {
            self.LOWER_MORTGAGE_PAYMENTS: LoanProfileV1.PURPOSES_OF_REFINANCE.rate_or_term,
            self.CASH_OUT: LoanProfileV1.PURPOSES_OF_REFINANCE.cash_out_other,
            self.HELOC: None,
            self.BOTH: LoanProfileV1.PURPOSES_OF_REFINANCE.cash_out_other,
        }[self.purpose]

    def is_cash_out(self):
        return self.purpose == self.CASH_OUT

    @property
    def mismo_purpose(self):
        return self.sample_TO_MISMO_REFINANCE_PURPOSE.get(self.purpose)

    @classmethod
    def mismo_to_sample_purpose(cls, purpose):
        return cls.MISMO_TO_sample_REFINANCE_PURPOSE.get(purpose)
