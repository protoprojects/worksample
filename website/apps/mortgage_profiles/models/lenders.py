# -*- coding: utf-8 -*-
from decimal import Decimal
from functools import partial
import logging

from django.core.urlresolvers import reverse
from django.db import models

from model_utils import Choices
from django.contrib.postgres.fields import JSONField
from shortuuidfield import ShortUUIDField

from core.models import TimeStampedModel
from core.utils import memoize, create_shortuuid
from money.models.fields import MoneyField
from .mortgage_profiles import MortgageProfile
from .aus_calculations import AusCalculations

logger = logging.getLogger('sample.mortech.models')

DEFAULT_CURRENCY = 'USD'

FLOOD_CERTIFICATION_FEE_DEFAULT = 0.0
PREPAID_INTEREST_DEFAULT = 0.0
TAX_SERVICE_FEE_DEFAULT = 69.0
TRUST_REVIEW_FEE_DEFAULT = 0.0
UNDERWRITING_FEE_DEFAULT = 0.0
ESTIMATED_APPRAISAL_FEE_DEFAULT = 550.0
TITLE_FEE_DEFAULT = 0.0
ESCROW_FEE_DEFAULT = 0.0
CREDIT_REPORT_FEE_DEFAULT = 0.0


class RateQuoteRequest(TimeStampedModel):
    """
    Stores each unique request for a rate quote. Handles retrieval of previously submitted
    rate quotes.
    """
    SCENARIO_RECOMMENDATION = {
        MortgageProfile.LONG_TERM: ('30 Year', 'Fixed'),
        MortgageProfile.MEDIUM_TERM: ('15 Year', 'Fixed'),
        MortgageProfile.SHORT_TERM: ('7 Year', 'Variable'),
        MortgageProfile.NOT_SURE: ('30 Year', 'Fixed'),
        '5 Year': ('5 Year', 'Variable')
    }

    mortgage_profile = models.ForeignKey(MortgageProfile, related_name="rate_quote_requests")
    uuid = ShortUUIDField(max_length=22, default=partial(create_shortuuid), blank=True, editable=False, unique=True)

    class Meta:
        ordering = ("-created",)
        verbose_name = "Rate Quote Request"
        verbose_name_plural = "All Rate Quote Requests"
        app_label = 'mortgage_profiles'

    def __unicode__(self):
        return u"Request for {} created on {}".format(self.mortgage_profile, self.created)

    def get_absolute_url(self):
        return reverse('mortgage_profiles:rate_quote', args=[self.uuid])

    def has_failed(self):
        # TODO: Negative references are ...not good. Rewrite as has_lenders()
        return not self.rate_quote_lenders.exists()

    def get_term_and_amortization(self):
        return self.SCENARIO_RECOMMENDATION[self.mortgage_profile.ownership_time]

    def get_rate_quote(self, term=None, amortization=None, rate=None):
        """
        Request a single lender product.

        May return None if a product is not found.

        If rate is specified, search for the best priced product at that rate.

        If rate is not specified, search for the best rate among the 5 products
        with a credit closest to par.
        """
        if not term and not amortization:
            term, amortization = self.get_term_and_amortization()

        queryset = self.rate_quote_lenders.filter(term=term, amortization_type=amortization)
        if rate:
            queryset = queryset.filter(rate=rate).order_by('points')
            result = queryset.first()
        else:
            queryset = queryset.filter(points__lte=0.0).order_by('-points', 'rate')
            if queryset.exists():
                queryset = queryset[:5]
                result = min(queryset, key=lambda item: item.rate)
            else:
                result = None

        return result

    def get_par_lender(self, term=None, amortization=None, rate=None):
        """Return single lender closest to par."""
        if not term and not amortization:
            term, amortization = self.get_term_and_amortization()

        par_lender = self.get_rate_quote(term, amortization)
        result = self.get_rate_quote(term, amortization, par_lender.rate) if par_lender else None

        return result

    def get_scenarios(self, term=None, amortization=None, rate=None):
        """Return top 5 of rate quotes by best price for given rate."""
        if not term and not amortization:
            term, amortization = self.get_term_and_amortization()
        price_range = ['25.0', '12.5', '0.0', '-12.5', '-25.0']
        results = []

        lender = self.get_rate_quote(term, amortization)
        if lender is not None:
            for price in price_range:
                new_rate = lender.rate + Decimal(price)
                current = self.get_rate_quote(term, amortization, new_rate)
                if current:
                    results.append(current)

            # Auto-update selected_rate_quote_lender only if new lenders available
            self.mortgage_profile.update_selected_lender()

        return results

    def get_lender_by_rate(self, rate, term=None, amortization=None):
        """Return best par lender by rate."""
        # get_rate_quote will have filtering refactored soon to mirror calls like this.
        # for now, it must mirror the calls in results.py as much as possible XXXkayhudson
        if not term and not amortization:
            term, amortization = self.get_term_and_amortization()

        return self.rate_quote_lenders.filter(
            term=term, amortization_type=amortization).filter(
                points__lte=0.0).filter(rate=rate).order_by('-points').first()

    @property
    def has_lenders(self):
        """Checks the request has lenders available."""
        return self.rate_quote_lenders.exists()

    def has_lender_product(self, term, amortization):
        """Checks the request has lenders with the specific term and amortization."""
        return self.rate_quote_lenders.filter(term=term, amortization_type=amortization).exists()


class RateQuoteLender(TimeStampedModel):
    """
    Model for Rate Quote API unique lender. Fees vary by lender and are configured on the Rate Quote account.

    Key:
    * piti = includles: principle, interest, mortgage_insurance (monthly_premium)
             excludes:  real estate taxes, insurance
    * monthly_premium = FHA/mortgage insurance
    * program_category = Results are returned by category, e.g. Conf 30 Yr, Non Conf 15 Yr
    * program_name = Name the lender gives their product, e.g. FNMA 30 Yr, Agency Fixed 30
    * program_type = FHA, VA, Conforming, Non Conforming
    """

    PROGRAM_TYPE_CHOICES = Choices(
        ('VA', 'va', 'VA'),
        ('FHA', 'fha', 'FHA'),
        ('Non Conforming', 'non_conforming', ['Non Conf', 'Non Conforming']),
        ('Conforming', 'conforming', ['Conf', 'Conforming']),
        ('Jumbo', 'jumbo', 'Jumbo'),
        ('Non-Agency', 'nonagency', 'Non-Agency'))

    FNM_PRODUCT_PLAN_IDENTIFIER = Choices(
        # For a complete list of ARM Index Codes, go to the Data Standards Supporting Resources
        # section of the Technology Integration
        # GEN06 = 6 Month
        # GEN1A = 1 yr, 1% annual cap
        # GEN1B = 1 yr, 2% annual cap
        # GEN3 = 3 yr"
        # (db value, accessor, human readable)
        ('GEN5', 'yr_5', '5 Year'),
        ('GEN7', 'yr_7', '7 Year'),
        # GEN10 = 10 yr
        # 251 = FHA 1 yr
        # FHAHY = FHA Hybrid ARM
        # VA1YR = VA 1 yr
        # VAARM = VA Hybrid ARM
        )

    AMORTIZATION_TYPE = Choices(('Fixed'), ('Variable'))

    TERM_CHOICES = Choices(
        # (db value, accessor, human readable)
        ('5 Year', 'yr_5', '5 Year'),
        ('7 Year', 'yr_7', '7 Year'),
        ('15 Year', 'yr_15', '15 Year'),
        ('30 Year', 'yr_30', '30 Year'))

    MISMO_TO_sample_AMORTIZATION_TYPE = {
        'Fixed': AMORTIZATION_TYPE.Fixed,
        'AdjustableRate': AMORTIZATION_TYPE.Variable,
    }

    TERM_TO_FNM_PRODUCT_PLAN_IDENTIFIER = {
        TERM_CHOICES.yr_5: FNM_PRODUCT_PLAN_IDENTIFIER.yr_5,
        TERM_CHOICES.yr_7: FNM_PRODUCT_PLAN_IDENTIFIER.yr_7,
    }

    sample_TO_MISMO_AMORTIZATION_TYPE = {value: key for key, value in MISMO_TO_sample_AMORTIZATION_TYPE.items()}

    request = models.ForeignKey(RateQuoteRequest, related_name="rate_quote_lenders")

    lender_name = models.CharField(max_length=255)
    amortization_type = models.CharField(max_length=255)  # AMORTIZATION_TYPE are choices
    apr = models.DecimalField(max_digits=10, decimal_places=6)
    fees = JSONField(null=True, blank=True)
    monthly_premium = MoneyField(max_digits=10, decimal_places=2, default_currency=DEFAULT_CURRENCY)
    piti = MoneyField(max_digits=10, decimal_places=2, default_currency=DEFAULT_CURRENCY, null=True)
    points = models.DecimalField(max_digits=9, decimal_places=6)
    price = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    program_category = models.CharField(max_length=255, blank=True)
    program_name = models.CharField(max_length=255)
    program_type = models.CharField(choices=PROGRAM_TYPE_CHOICES, max_length=255)
    rate = models.DecimalField(max_digits=10, decimal_places=6)
    term = models.CharField(max_length=255)  # TERM_CHOICES
    upfront_fee = MoneyField(max_digits=10, decimal_places=2, default_currency=DEFAULT_CURRENCY, null=True)

    class Meta:
        ordering = ("-created",)
        verbose_name = "Rate Quote Lender"
        verbose_name_plural = "Rate Quote Lenders"
        app_label = 'mortgage_profiles'

    def __unicode__(self):
        return u"ID: {} -- Term: {}, amortization: {}, program type: {}".format(
            self.id, self.term, self.amortization_type, self.program_type)

    ##################
    #  related objs  #
    ##################
    @property
    def mortgage_profile(self):
        return self.request.mortgage_profile.subclass

    @property
    def primary_borrower(self):
        return self.request.mortgage_profile.subclass.loan_profilev1.primary_borrower

    @property
    def primary_coborrower(self):
        return self.request.mortgage_profile.subclass.loan_profilev1.primary_coborrower

    @property
    @memoize
    def aus_calculations(self):
        return AusCalculations(self)

    ######################
    #  other properties  #quotel
    ######################
    @property
    def qualifying_rate(self):
        """
        qualifying_rate is the interest rate used to calculate the monthly loan payment for underwriting.

        If the mortgage is a "3 Year" or "5 year" ARM, the qualifying_rate is 2 percent higher than the actual rate.
        Otherwise, the qualifying_rate is the same as the rate (also called the note_rate).

        The rational for adding the 2 percent margin is to ensure that the borrower has enough income to make the
        required payments even if rates rise after the initial 3 or 5 year fixed period.
        """
        adjustment = Decimal('2.00') if self.term in ('3 Year', '5 Year') else Decimal('0.00')
        return Decimal(self.rate / 100) + adjustment

    ######################
    #  monthly payments  #
    ######################
    @property
    def escrowed_insurance(self):
        """Details: Loan amount * 0.00375 / 12"""
        return Decimal(self.mortgage_profile.get_loan_amount()) * Decimal(0.00375 / 12)

    @property
    def escrowed_taxes(self):
        """Details: Property value * 0.0125 / 12"""
        return Decimal(self.mortgage_profile.get_property_value() * 0.0125 / 12)

    @property
    def monthly_payment(self):
        """represents principal and interest only"""
        if self.monthly_premium:
            return self.piti - self.monthly_premium
        return self.piti

    ##########
    #  fees  #
    ##########
    def _get_fee(self, fee_names, default_fee=0):
        '''Returns the name of the fee or returns None.'''
        fees = self.fees if self.fees else {}
        for fee_name in fee_names:
            if fee_name in fees:
                return fees.get(fee_name, default_fee)
        return default_fee

    @property
    def underwriting_fee(self):
        '''Returns fee value. If no fee exists, returns value of 0 for rate quote calculations.'''
        names = [
            'Admin',
            'Admin Fee',
            'Administration',
            'Administration Fee',
            'Commitment',
            'FMC Origination',
            'Funding Fee',
            'Lender Fee',
            'Lender Fees',
            'Underwriting Fee',
            'UW Fee']
        return self._get_fee(names, UNDERWRITING_FEE_DEFAULT)

    @property
    def prepaid_interest(self):
        '''Returns pre-paid interest.'''
        names = ['Pre-paid Interest', 'Pre-paid Interest (15 days)']
        return self._get_fee(names, PREPAID_INTEREST_DEFAULT)

    @property
    def tax_service_fee(self):
        '''Return tax service fee. Default value is 69.'''
        return self._get_fee(['Tax Service Fee'], TAX_SERVICE_FEE_DEFAULT)

    @property
    def flood_certification(self):
        '''Return flood certification.'''
        return self._get_fee(['Flood Certification'], FLOOD_CERTIFICATION_FEE_DEFAULT)

    @property
    def trust_review_fee(self):
        return self._get_fee(['Trust Review Fee'], TRUST_REVIEW_FEE_DEFAULT)

    @property
    def estimated_appraisal_fee(self):
        return self._get_fee(['Estimated Appraisal Fee'], ESTIMATED_APPRAISAL_FEE_DEFAULT)

    @property
    def title_fee(self):
        return self._get_fee(['Title Fee'], TITLE_FEE_DEFAULT)

    @property
    def escrow_fee(self):
        return self._get_fee(['Escrow Fee'], ESCROW_FEE_DEFAULT)

    @property
    def credit_report_fee(self):
        return self._get_fee(['Credit Report'], CREDIT_REPORT_FEE_DEFAULT)

    def get_relative_points(self):
        return None if self.points is None else (self.points - 100.0)

    ####################
    #  boolean checks  #
    ####################
    def is_variable(self):
        return self.amortization_type == self.AMORTIZATION_TYPE.Variable

    def is_fixed(self):
        return self.amortization_type == self.AMORTIZATION_TYPE.Fixed

    def is_jumbo(self):
        '''Return Jumbo program status.'''
        return self.program_type in [self.PROGRAM_TYPE_CHOICES.jumbo, self.PROGRAM_TYPE_CHOICES.nonagency]

    def is_FHA(self):
        """
        Return bool, if lender program type is FHA compatible.

        """
        return self.program_type == self.PROGRAM_TYPE_CHOICES.fha

    def is_VA(self):
        """
        Return bool, if lender program type is VA compatible.

        """
        return self.program_type == self.PROGRAM_TYPE_CHOICES.va

    ##########
    #  mismo #
    ##########
    def mismo_amortization_type(self):
        return self.sample_TO_MISMO_AMORTIZATION_TYPE.get(self.amortization_type)

    def mismo_fnm_product_plan_identifier(self):
        """
        maps a the term (ie '5 Year' or '7 Year) to a FNM product identifier (ie GEN5 or GEN7)

        note: for a complete list of ARM Index Codes, see FNM_PRODUCT_PLAN_IDENTIFIER above
        """
        return None if self.is_fixed() else self.TERM_TO_FNM_PRODUCT_PLAN_IDENTIFIER.get(self.term)

    @classmethod
    def mismo_to_sample_amortization_type(cls, amortization_type):
        return cls.MISMO_TO_sample_AMORTIZATION_TYPE.get(amortization_type)
