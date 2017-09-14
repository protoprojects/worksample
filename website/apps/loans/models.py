# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from decimal import Decimal
import hmac
import logging
import re
import time
import uuid

from dateutil.relativedelta import relativedelta

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import force_str, python_2_unicode_compatible

from model_utils import Choices
from model_utils.fields import MonitorField

from django_postgres_pgpfields.fields import TextPGPPublicKeyField
from django_postgres_pgpfields.managers import PGPEncryptedManager


from rest_framework import exceptions

from encompass.client import EncompassClient
from box.api_v1 import archive_credit_report_storage
from core.models import TimeStampedModel
from core.fields import CustomArrayField
from encompass.client import EncompassConfig, EncompassClient
from money.models.fields import MoneyField
from mismo_credit.models import CreditRequestResponse
from storage.models import Storage


logger = logging.getLogger('sample.loans.models')

DEFAULT_CURRENCY = 'USD'
PHONE_RE = re.compile(r'[^\d]')


# updated mixins/models follow
def _get_years_months(start_date, end_date):
    if start_date is None:
        retval = (None, None)
    else:
        end = datetime.datetime.today() if end_date is None else end_date
        years = end.year - start_date.year
        months = end.month - start_date.month
        if end.month < start_date.month:
            years -= 1
            months += 12
        retval = (years, months)
    return retval


# V1 suffix to reduce migration headaches and to avoid storage breakage
class LoanProfilePurposeOfLoanMixinV1(models.Model):
    class Meta:
        abstract = True
    # In Mismo, LoanProfileV1.property_purpose equates to LOAN_PURPOSE/@PropertyUsageType
    # MISMO 2.3.1 and Fannie MISMO 2.3.1 are the same for LOAN_PURPOSE/@PropertyUsageType
    # The sample values originate from the MA Portal implementation
    sample_PROPERTY_PURPOSES = Choices(
        ('investment', 'investor', 'Investor'),
        ('primary_residence', 'primary_residence', 'Primary Residence'),
        ('secondary_residence', 'second_home', 'Second Home'),
    )

    MISMO_PROPERTY_USAGE = Choices(
        ('PrimaryResidence', 'Primary Home'),
        ('SecondHome', 'Second Home'),
        ('Investor', 'Investment Property'),
    )

    sample_PROPERTY_PURPOSE_TO_MISMO_PROPERTY_USAGE = {
        sample_PROPERTY_PURPOSES.investor: MISMO_PROPERTY_USAGE.Investor,
        sample_PROPERTY_PURPOSES.primary_residence: MISMO_PROPERTY_USAGE.PrimaryResidence,
        sample_PROPERTY_PURPOSES.second_home: MISMO_PROPERTY_USAGE.SecondHome,
    }

    MISMO_PROPERTY_USAGE_TO_sample_PROPERTY_PURPOSE = {
        MISMO_PROPERTY_USAGE.Investor: sample_PROPERTY_PURPOSES.investor,
        MISMO_PROPERTY_USAGE.PrimaryResidence: sample_PROPERTY_PURPOSES.primary_residence,
        MISMO_PROPERTY_USAGE.SecondHome: sample_PROPERTY_PURPOSES.second_home,
    }

    LOAN_PURPOSES = (
        'ConstructionToPermanent',
        'NoCash-Out Refinance',
        'Purchase',
        'ConstructionOnly',
        'Cash-Out Refinance',
        'Other')

    PURPOSES_OF_REFINANCE = Choices(
        'cash_out_debt_consolidation',
        'cash_out_home_improvement',
        'cash_out_other',
        'rate_or_term',
        'fha_streamlined',
        'va_irrrl')

    PURPOSE_OF_LOAN = Choices('purchase', 'refinance')

    ESTATE_WILL_BE_HELD_CHOICES = Choices(
        'fee_simple',
        'leasehold')

    OTHER_ON_LOAN_CHOICES = Choices('spouse_or_partner', 'someone_else', 'no')

    APPLICATION_TAKEN_METHOD_CHOICES = Choices(
        ('FaceToFace', 'face_to_face', 'FaceToFace'),
        ('Internet', 'internet', 'Internet'),
        ('Telephone', 'telephone', 'Telephone'))

    notes = models.TextField(blank=True)

    property_value_estimated = MoneyField(
        blank=True, null=True, default_currency=DEFAULT_CURRENCY, max_digits=10,
        decimal_places=2, default=None)
    refinance_year_acquired = models.PositiveIntegerField(blank=True, null=True)
    refinance_original_cost = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY, max_digits=10,
                                         decimal_places=2, default=None)
    refinance_amount_of_existing_liens = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                                                    max_digits=10, decimal_places=2, default=None)
    purpose_of_refinance = models.TextField(blank=True, null=True)  # PURPOSES_OF_REFINANCE

    is_cash_out = models.NullBooleanField()
    cash_out_amount = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                                 max_digits=10, decimal_places=2, default=None)
    is_already_in_contract = models.NullBooleanField()
    is_down_payment_subordinate_finances_used = models.NullBooleanField()
    down_payment_amount = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                                     max_digits=10, decimal_places=2, default=None)
    down_payment_source = models.TextField(max_length=50, blank=True)
    deposit_company_name = models.CharField(max_length=100, blank=True)
    deposit_cash_value = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                                    max_digits=10, decimal_places=2, default=None)

    new_property_address = models.ForeignKey('AddressV1', null=True, blank=True,
                                             on_delete=models.SET_NULL)
    is_refinancing_current_address = models.NullBooleanField()
    new_property_info_contract_purchase_price = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                                                           max_digits=10, decimal_places=2, default=None)
    are_accounts_filling_jointly = models.NullBooleanField()

    application_taken_method = models.CharField(
        choices=APPLICATION_TAKEN_METHOD_CHOICES,
        default=APPLICATION_TAKEN_METHOD_CHOICES.telephone,
        max_length=16)

    is_demographics_questions_request_confirmed = models.NullBooleanField()

    property_purpose = models.CharField(max_length=100, blank=True)  # LOAN_PURPOSE/@PropertyUsageType
    # purpose_of_loan should be a choice field of PURPOSE_OF_LOAN
    purpose_of_loan = models.CharField(max_length=100, blank=True)
    how_title_will_be_held = models.CharField(max_length=50, blank=True)
    how_estate_will_be_held = models.CharField(
        choices=ESTATE_WILL_BE_HELD_CHOICES,
        default=ESTATE_WILL_BE_HELD_CHOICES.fee_simple,
        max_length=10)
    leasehold_expiration_date = models.DateField(null=True, blank=True,
                                                 validators=[MinValueValidator(EncompassConfig.MIN_DATE),
                                                             MaxValueValidator(EncompassConfig.MAX_DATE)])

    mortgage_type = models.CharField(max_length=100, blank=True)
    other_mortgage_type_description = models.CharField(max_length=100, blank=True)
    base_loan_amount = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                                  max_digits=10, decimal_places=2, default=None)
    requested_interest_rate_percent = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True)
    loan_amortization_term_months = models.PositiveIntegerField(blank=True, null=True)

    loan_amortization_type = models.CharField(max_length=100, blank=True)
    other_amortization_type_description = models.CharField(max_length=100, blank=True)
    arm_type_description = models.CharField(max_length=100, blank=True)
    gpm_years = models.PositiveIntegerField(blank=True, null=True)
    gpm_rate = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # fields for customer_portal
    other_on_loan = models.CharField(max_length=30, choices=OTHER_ON_LOAN_CHOICES, null=True)

    @property
    def mismo_property_usage(self):  # LOAN_PURPOSE/@PropertyUsageType
        return self.sample_PROPERTY_PURPOSE_TO_MISMO_PROPERTY_USAGE.get(self.property_purpose)

    @classmethod
    def mismo_to_sample_property_purpose(cls, property_usage):
        return cls.MISMO_PROPERTY_USAGE_TO_sample_PROPERTY_PURPOSE.get(property_usage)


class LoanProfileV1Manager(models.Manager):
    def uniquifier_generate(self, loan_profile):
        h = hmac.new(str(loan_profile.id))
        borrower = loan_profile.borrowers.first()
        if borrower:
            h.update(force_str(borrower.username))
        advisor = loan_profile.advisor
        if advisor:
            h.update(force_str(advisor.username))
        while True:
            h.update(str(time.time()))
            uniquifier = h.hexdigest()[:4]
            if not self.get_queryset().filter(uniquifier=uniquifier).exists():
                break
        return uniquifier


# pylint: disable=too-many-public-methods
# pylint: disable=too-many-instance-attributes
@python_2_unicode_compatible
class LoanProfileV1(LoanProfilePurposeOfLoanMixinV1, TimeStampedModel):
    """Information not directly associated with the loan itself"""

    ENCOMPASS_NEVER_SYNCED = 'NEVER_SYNCED'
    ENCOMPASS_SYNCED = 'SYNCED'
    ENCOMPASS_SYNC_IN_PROGRESS = 'SYNC_IN_PROGRESS'
    ENCOMPASS_READY_TO_SYNC = 'READY_TO_SYNC'
    ENCOMPASS_SYNC_FAILED = 'SYNC_FAILED'

    ENCOMPASS_SYNC_CHOICES = (
        (ENCOMPASS_NEVER_SYNCED, ENCOMPASS_NEVER_SYNCED),
        (ENCOMPASS_SYNCED, ENCOMPASS_SYNCED),
        (ENCOMPASS_SYNC_IN_PROGRESS, ENCOMPASS_SYNC_IN_PROGRESS),
        (ENCOMPASS_READY_TO_SYNC, ENCOMPASS_READY_TO_SYNC),
        (ENCOMPASS_SYNC_FAILED, ENCOMPASS_SYNC_FAILED),
    )

    ASSETS_VERIFICATION_METHOD_CHOICES = Choices(
        ('self_reported', 'Self Reported'),
        ('yodlee', 'Yodlee Aggregated assets')
    )

    LOCK_OWNER_CHOICES = Choices('advisor', 'customer')
    CRM_OBJECT_TYPE_CHOICES = Choices('lead', 'opportunity')
    SOURCE_CHOICES = Choices('advisor_portal', 'customer_portal')

    advisor = models.ForeignKey('accounts.Advisor', related_name='loan_profilesV1', null=True,
                                on_delete=models.SET_NULL)
    customer = models.ForeignKey('accounts.Customer', related_name='loan_profilesv1', blank=True, null=True,
                                 on_delete=models.SET_NULL)
    storage = models.ForeignKey('storage.Storage', related_name='loan_profilesv1', blank=True, null=True,
                                on_delete=models.SET_NULL)
    lead = models.ForeignKey('Lead', related_name='loan_profilesv1', blank=True, null=True)

    uniquifier = models.CharField(max_length=8, blank=True)
    is_active = models.BooleanField(default=True)
    guid = models.UUIDField(
        primary_key=False,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )

    lock_owner = models.CharField(choices=LOCK_OWNER_CHOICES, default=LOCK_OWNER_CHOICES.advisor, max_length=20)
    lock_owner_updated = MonitorField(monitor='lock_owner', null=True, default=None)
    los_name = models.CharField(null=True, blank=True, max_length=64)
    los_guid = models.CharField(null=True, blank=True, max_length=128)

    crm_id = models.CharField(max_length=255, blank=True)
    crm_type = models.CharField(max_length=255, blank=True)
    crm_object_type = models.CharField(choices=CRM_OBJECT_TYPE_CHOICES,
                                       default=CRM_OBJECT_TYPE_CHOICES.lead, max_length=16)
    crm_last_sent = models.DateTimeField(null=True, blank=True)

    datetime_sent_to_encompass = models.DateTimeField(null=True, blank=True)
    datetime_synced_with_encompass = models.DateTimeField(null=True, blank=True)
    encompass_sync_status = models.CharField(
        choices=ENCOMPASS_SYNC_CHOICES, default=ENCOMPASS_NEVER_SYNCED,
        max_length=100, blank=True,
    )

    _respa_triggered = models.BooleanField(default=False)
    respa_triggered_at = MonitorField(monitor='_respa_triggered', when=[True], null=True, default=None)

    credit_report_xml_storage = models.ForeignKey('storage.Storage', related_name='+',
                                                  blank=True, null=True,
                                                  on_delete=models.SET_NULL)
    prequal_letter_storage = models.OneToOneField('storage.Storage',
                                                  related_name='loan_profile',
                                                  on_delete=models.SET_NULL,
                                                  null=True,
                                                  blank=True)
    assets_verification_method = models.CharField(
        choices=ASSETS_VERIFICATION_METHOD_CHOICES,
        max_length=127,
        null=True,
        blank=True
    )

    objects = LoanProfileV1Manager()

    def __str__(self):
        return "id: {0}, is active: {1}, encompass_sync_status: {2}".format(
            self.id, self.is_active, self.encompass_sync_status
        )

    def _create_storage_criteria(self):
        return {
            'is_active': self.is_active,
            'storage_is_none': self.storage_id is None,
            'has_borrower': self.borrowers.filter(is_active=True).exists(),
        }

    def _can_create_storage(self):
        return all(self._create_storage_criteria().values())

    def create_storage(self, *args, **kwargs):
        logger.debug('LOAN-PROFILE-CREATE-STORAGE lp %s can_create %s criteria %s',
                     self.guid, self._can_create_storage(), self._create_storage_criteria())
        if self._can_create_storage():
            if not self.uniquifier:
                self.uniquifier = LoanProfileV1.objects.uniquifier_generate(self)
            storage = Storage.objects.get_or_create_loan_profile_storage(self)
            if not storage:
                logger.debug('LOAN-PROFILE-NO-STORAGE-RETURNED lp %s', self.guid)
                return
            storage.save()
            logger.debug('LOAN-PROFILE-SAVE-STORAGE-SAVED lp %s storage_id %d', self.guid, storage.id)
            # pylint: disable=attribute-defined-outside-init
            self.storage_id = storage.id
        logger.debug('LOAN-PROFILE-SAVE-SAVING lp %s', self.guid)
        super(LoanProfileV1, self).save(*args, **kwargs)
        self.refresh_from_db()

    def is_purchase(self):
        return self.purpose_of_loan == self.PURPOSE_OF_LOAN.purchase

    def is_refinance(self):
        return self.purpose_of_loan == self.PURPOSE_OF_LOAN.refinance

    def is_prequalified(self):
        return False if self.aus_request_response is None else self.aus_request_response.is_prequalified
    is_prequalified.boolean = True  # for use in admin to make it appear as a checkbox

    def has_customer(self):
        return self.customer_id is not None

    def transfer_lock_to_advisor(self):
        self.lock_owner = self.LOCK_OWNER_CHOICES.advisor
        self.save()

    ################
    #  properties  #
    ################
    @property
    def source(self):
        return self.SOURCE_CHOICES.customer_portal if self.has_customer() else self.SOURCE_CHOICES.advisor_portal

    @property
    def subject_property_address(self):
        if self.is_refinance():
            if self.is_refinancing_current_address is None:
                retval = None
            elif self.is_refinancing_current_address:
                borrower = self.borrowers.first()
                retval = borrower and getattr(borrower, 'address')
            else:
                retval = self.new_property_address
        elif self.is_purchase():
            retval = self.new_property_address
        else:
            retval = None
        return retval

    @property
    def loan_purpose(self):
        if self.is_refinance():
            if self.purpose_of_refinance:
                retval = ('cash_out_refinance'
                          if self.purpose_of_refinance.startswith('cash_out_') else
                          'no_cash_out_refinance')
            else:
                # Unknown at this point. There is no plain "refinance"
                retval = ''
        else:
            retval = self.purpose_of_loan
        return retval

    @property
    def is_customer_lock_owner(self):
        return self.lock_owner == self.LOCK_OWNER_CHOICES.customer

    @property
    def is_advisor_lock_owner(self):
        return self.lock_owner == self.LOCK_OWNER_CHOICES.advisor

    @property
    def primary_borrower(self):
        return self.borrowers.filter(is_active=True).first()

    @property
    def primary_coborrower(self):
        return self.primary_borrower.get_active_coborrower()

    @property
    def has_storage(self):
        return bool(self.storage)

    @property
    def selected_rate_quote_lender(self):
        if self.current_mortgage_profile:
            return self.current_mortgage_profile.selected_rate_quote_lender

    ##########################
    # mortgage profile stuff #
    #########################
    @property
    def mortgage_profile(self):
        # This should be removed, but need to check for usage first...
        return self.mortgage_profiles.first()

    @property
    def current_mortgage_profile(self):
        return self.mortgage_profiles.select_subclasses().order_by('-created').first()

    def update_from_mortgage_profile(self, include_lender=True):
        '''Update from a mortgage profile and, optionally, the selected lender'''
        update_fields = self._update_from_mortgage_profile_fields()
        if include_lender:
            update_fields.extend(self._update_from_rate_quote_lender_fields())
        if update_fields:
            self.save(update_fields=update_fields)
        return update_fields

    def _resolve_property_purpose(self, mortgage_profile):
        '''Attempt to resolve discrepancy between property usage and declaration

        If the declaration is True, then go with primary residence.
        Otherwise go with the property usage.

        This means that when the declaration is False we may still list it as
        being for a primary residence.

        '''
        borrower = self.primary_borrower
        plans_primary_occupancy = (
            borrower.demographics.plans_to_occupy_as_primary_residence
            if borrower and borrower.demographics_id
            else None)
        property_purpose = (
            self.sample_PROPERTY_PURPOSES.primary_residence
            if plans_primary_occupancy
            else self.mismo_to_sample_property_purpose(mortgage_profile.mismo_property_usage))
        if plans_primary_occupancy is False:
            logger.warning('DECLARATION-L-FALSE-USAGE-PRIMARY %s', self.guid)
        return property_purpose

    def _update_from_mortgage_profile_fields(self):
        '''Update fields based on the current mortgage profile

        Updates but does not save the loan profile.

        Return
        - sequence of updated fields

        Usage
        - When initializing a loan profile from a mortgage profile
        - When the lock holder changes from the consumer

        '''
        update_fields = []
        mortgage_profile = self.current_mortgage_profile
        if mortgage_profile:
            self.purpose_of_loan = mortgage_profile.kind
            property_purpose = self._resolve_property_purpose(mortgage_profile)
            self.property_purpose = property_purpose or ''
            self.base_loan_amount = mortgage_profile.get_loan_amount()
            self.property_value_estimated = mortgage_profile.get_property_value()
            update_fields.extend([
                'purpose_of_loan',
                'property_purpose',
                'base_loan_amount',
                'property_value_estimated',
            ])
        if mortgage_profile and mortgage_profile.is_refinance:
            self.property_value_estimated = mortgage_profile.get_property_value()
            self.is_cash_out = mortgage_profile.is_cash_out()
            self.purpose_of_refinance = mortgage_profile.get_loan_profile_purpose_of_refi()
            self.refinance_amount_of_existing_liens = mortgage_profile.mortgage_owe
            update_fields.extend([
                'is_cash_out',
                'purpose_of_refinance',
                'refinance_amount_of_existing_liens',
            ])
            if self.is_cash_out:
                self.cash_out_amount = mortgage_profile.cashout_amount
                update_fields.append('cash_out_amount')
        if mortgage_profile and mortgage_profile.is_purchase:
            self.down_payment_amount = mortgage_profile.purchase_down_payment
            self.new_property_info_contract_purchase_price = mortgage_profile.target_value
            update_fields.extend([
                'down_payment_amount',
                'new_property_info_contract_purchase_price',
            ])
        return update_fields

    def _update_from_rate_quote_lender_fields(self):
        '''Update fields based on the selected rate quote lender

        Updates but does not save the loan profile.

        Return
        - sequence of updated fields

        Usage
        - When the lock holder changes from the consumer

        '''
        update_fields = []
        lender = self.selected_rate_quote_lender
        if lender:
            # program type
            if lender.program_type in ('FHA', 'VA'):
                self.mortgage_type = lender.program_type
                update_fields.append('mortgage_type')
            elif lender.program_type.startswith('Conf'):
                self.mortgage_type = 'Conventional'
                update_fields.append('mortgage_type')
            else:
                self.mortgage_type = 'Other'
                self.other_mortgage_type_description = lender.program_type
                update_fields.extend(['mortgage_type', 'other_mortgage_type_description'])
            # interest rate
            self.requested_interest_rate_percent = lender.rate / Decimal('100.0')
            update_fields.append('requested_interest_rate_percent')
            # amortization term
            if lender.term == '15 Year':
                self.loan_amortization_term_months = 15 * 12
                update_fields.append('loan_amortization_term_months')
            elif lender.term in ('5 Year', '7 Year', '30 Year'):
                self.loan_amortization_term_months = 30 * 12
                update_fields.append('loan_amortization_term_months')
            # amortization type
            if lender.amortization_type == 'Fixed':
                self.loan_amortization_type = 'Fixed Rate'
                update_fields.append('loan_amortization_type')
            elif lender.amortization_type == 'Variable':
                self.loan_amortization_type = 'ARM'
                self.arm_type_description = lender.term
                update_fields.extend(['arm_type_description', 'loan_amortization_type'])
        return update_fields

    #####################
    #  encompass stuff  #
    #####################
    @property
    def is_encompass_synced(self):
        return self.los_guid and (self.encompass_sync_status == self.ENCOMPASS_SYNCED)

    def encompass_never_synced_or_failed(self):
        return self.encompass_sync_status in [
            self.ENCOMPASS_NEVER_SYNCED,
            self.ENCOMPASS_SYNC_FAILED,
        ]

    def _check_purchase_price(self):
        '''Check the purchase price is set when the down payment is set

        Only applies to purchases

        '''
        retval = None
        if self.is_purchase() and self.down_payment_amount:
            purchase_price = getattr(
                self, 'new_property_info_contract_purchase_price', None)
            has_valid_purchase_price = purchase_price and (0 <= purchase_price)
            if not has_valid_purchase_price:
                retval = 'Down payment amount requires a purchase price'
        return retval

    def _check_refinance_purpose(self):
        if self.is_refinance() and self.purpose_of_refinance is None:
            retval = 'Refinance purpose is not set'
        else:
            retval = None
        return retval

    def _check_subject_property(self):
        '''Check for subject property address city, state, and zip

        Return
            None - no issues
            string - message about what is wrong

        '''
        subject_property_address = self.subject_property_address
        if subject_property_address is None:
            retval = 'Subject property is not set'
        elif not subject_property_address.state:
            retval = 'Subject property state is not set'
        else:
            retval = None
        return retval

    def get_encompass_loan(self):
        if not self.los_guid:
            return None

        encompass_client = EncompassClient()
        return encompass_client.loan(self.los_guid)

    def encompass_sync_warnings(self):
        checks = (
            self._check_purchase_price,
            self._check_refinance_purpose,
            self._check_subject_property)
        return [check() for check in checks if check()]

    def can_sync_to_encompass(self, exception_cls=None):
        """Check whether the available data allows for syncing to encompass.

        Arguments
            exception_cls [optional] - exception to raise on failure

        Return
            bool - True on success; False on failure (or raise exception_cls)

        If called from a view, the exception should be a DRF validationError.
        For other contexts, e.g., a celery task, the exception should be a
        LoanSyncException.

        """
        warnings = self.encompass_sync_warnings()
        retval = len(warnings) == 0
        if not retval and (exception_cls is not None):
            raise exception_cls(warnings[0])
        return retval

    def los_sync(self):
        """DO NOT USE DIRECTLY. This is used in celery task
         For directly call use self.sync_to_encompass"""
        # XXXwalrus highly ughly
        import encompass.synchronization.loans_sync as loans_sync
        if not self.los_guid:
            if not hasattr(self, 'loanv1'):
                # pylint: disable=attribute-defined-outside-init
                self.loanv1 = LoanV1(loan_profile=self)
                self.loanv1.save()

            fields = loans_sync.LoanSynchronizationV1(self.loanv1).get_data()
            encompass_loan_data = {
                'test_mode': str(EncompassConfig.TEST_MODE),
                'fields': fields
            }

            if self.respa_triggered:
                # if encompass_loan_data['test_mode'] is True 'Testing_Training' folder would be used
                encompass_loan_data['loan_folder'] = 'My Pipeline'

            officer_id = getattr(self.advisor, 'encompass_id', None)
            if officer_id:
                encompass_loan_data['officer_id'] = officer_id

            encompass_client = EncompassClient()
            encompass_loan = encompass_client.create_loan(encompass_loan_data)

            if encompass_loan.guid:
                self.los_guid = encompass_loan.guid
                self.los_name = EncompassConfig.LOS_NAME
            super(LoanProfileV1, self).save()

            if all([EncompassConfig.EXPLICITLY_ASSIGN_ADVISOR,
                    encompass_loan.guid,
                    officer_id]):
                encompass_loan.change_officer(officer_id)

        return self.los_guid

    def sync_to_encompass(self):
        """
        use this method to sync to encompass.

        we have a celery beat that calls sync_all_loan_profiles_with_encompass, which
        walks over the loan_profiles checking for encompass_sync_status == ENCOMPASS_READY_TO_SYNC
        and then calls the sub task sync_loan_profile_with_encompass (which in turn calls self.los_sync()).

        calling sync_loan_profile_with_encompass directly is problematic because if it fails,
        there is no way to guarantee that the task will be restarted or retried.  Hence, the celery beat.
        """
        can_sync = self.can_sync_to_encompass()
        if can_sync:
            self.encompass_sync_status = LoanProfileV1.ENCOMPASS_READY_TO_SYNC
            self.save()
        return can_sync

    ################
    # credit stuff #
    ################
    def find_valid_credit_report_summary(self):
        report = None
        summary = self.credit_report_summaries.filter(is_active=True).order_by('-created').first()
        if summary:
            scores_record = summary.credit_report_scores.first()
            if scores_record and scores_record.has_scores():
                report = summary

        return report

    @property
    def valid_credit_request(self):
        credit_request = None
        summary = self.find_valid_credit_report_summary()
        if summary:
            credit_request = summary.credit_request_response
        return credit_request

    @property
    def valid_credit_report_score(self):
        score_report = None
        summary = self.find_valid_credit_report_summary()
        if summary:
            score_report = summary.credit_report_scores.first()
        return score_report

    def archive_existing_credit_report(self):
        """
        Archive and invalidate an existing credit report or report Attempt
        to avoid Storage name collisions.

        TODO: ENG-55 - make sure this works - currently it seems to pass the
        credit_report_xml_storage name instead of the storage itself.
        """
        if self.credit_report_summaries.filter(is_active=True).exists():
            # if we have a report, archive the files, invalidate the summary
            report = self.credit_report_summaries.filter(is_active=True).first()
            report.archive()
        else:
            # if no summary, check the xml communication file, archive it
            if self.credit_report_xml_storage:
                archive_credit_report_storage(self.credit_report_xml_storage)

        # in both cases null out the xml communication file storage
        self.credit_report_xml_storage = None
        self.save()

    def get_credit_request_in_progress(self):
        '''
        Check to see if there is a request job that is running or about to be run
        '''
        outstanding_statuses = (
            CreditRequestResponse.JOB_READY,
            CreditRequestResponse.JOB_RUNNING)
        credit_requests_outstanding = self.credit_request_responses.order_by('-created').filter(
            status__in=outstanding_statuses)
        return credit_requests_outstanding

    def are_credit_retries_exceeded(self):
        '''
        Count the number of tries, False if 3 or more.
        '''
        return self.credit_request_responses.count() >= 3

    def set_credit_retries_exceeded(self):
        '''
        Set the most recent status to retries exceeded status
        '''
        last_request = self.credit_request_responses.order_by('-created').first()
        if last_request.status != CreditRequestResponse.JOB_RETRIES_ERROR:
            job = CreditRequestResponse.objects.create(
                loan_profile=self, credit_system=CreditRequestResponse.CBC_CODE,
                status=CreditRequestResponse.JOB_RETRIES_ERROR)
            job.save()

    #############
    # aus stuff #
    #############
    @property
    def aus_request_response(self):
        """
        retrieves the most recent aus_request_response

        notes:
         - unlike credit, we want the most recent AUS request, NOT the most recent successful one.
           older AUS requests may rely on outdated data.
        """
        return self.aus_request_responses.order_by('-created').first()

    def get_mortgage_liabilities(self):
        """
        gets all unique mortgage liabilities for borrower and coborrower
        eliminating duplicates by checking against account_identifier and holder_name
        """
        # get mortgage liabilities for borrower or coborrower
        mortgages = LiabilityV1.objects.filter(kind=LiabilityV1.MORTGAGE_LOAN)
        if self.primary_coborrower:
            mortgages = mortgages.filter(
                models.Q(borrowerv1=self.primary_borrower) | models.Q(coborrowerv1=self.primary_coborrower))
        else:
            mortgages = mortgages.filter(borrowerv1=self.primary_borrower)

        # find unique values
        unique_values = set([(mortgage.account_identifier, mortgage.holder_name) for mortgage in mortgages])

        # return unique mortgage liabilities
        results = []
        for mortgage in mortgages:
            value = (mortgage.account_identifier, mortgage.holder_name)
            if value in unique_values:
                results.append(mortgage)
                unique_values.discard(value)
        return results

    def run_aus(self):
        import mismo_aus.tasks as tasks
        return tasks.start_aus_pull(self)

    ###############
    # respa stuff #
    ###############
    def respa_criteria_for_consumer_portal(self):
        '''Check all the criteria required to trigger respa for the consumer portal.

        MUY IMPORTANTE: To ensure correct values are used in the determining,
        this should be called *after* self.update_from_mortgage_profile().

        '''
        has_borrower_ssn = bool(self.primary_borrower.ssn) if self.primary_borrower else None
        is_primary_residence = ((self.property_purpose == self.sample_PROPERTY_PURPOSES.primary_residence)
                                if self.property_purpose
                                else None)
        is_refinance = (self.is_refinance() if self.purpose_of_loan else None)
        return {'has_borrower_ssn': has_borrower_ssn,
                'is_refinance': is_refinance,
                'is_primary_residence': is_primary_residence}

    def respa_criteria_for_advisor_portal(self):
        """
        Check all the criteria required to trigger respa for the advisor portal.
        https://app.asana.com/0/26423929888212/167519965037604
        """

        criteria = {
            'has_property_value': bool(self.property_value_estimated or self.new_property_info_contract_purchase_price),
            'address_is_complete': bool(self.subject_property_address.is_mismo_complete() if self.subject_property_address else None),
            'has_base_loan_amount': bool(self.base_loan_amount),
            'has_base_income': False,
            'has_borrower_ssn': False,
            'borrower_first_name_filled': False,
            'borrower_last_name_filled': False,
        }

        if self.primary_borrower:
            criteria['has_base_income'] = bool(self.primary_borrower.get_base_income_with_not_empty_value())
            criteria['has_borrower_ssn'] = bool(self.primary_borrower.ssn)
            criteria['borrower_first_name_filled'] = bool(self.primary_borrower.first_name)
            criteria['borrower_last_name_filled'] = bool(self.primary_borrower.last_name)

        return criteria

    def can_trigger_respa_for_consumer_portal(self):
        return all(self.respa_criteria_for_consumer_portal().values())

    def can_trigger_respa_for_advisor_portal(self):
        return all(self.respa_criteria_for_advisor_portal().values())

    def trigger_respa_for_consumer_portal(self):
        """
        USED TO TRIGGER RESPA for CONSUMER PORTAL apps
        this method will trigger respa as long as the below critieria are met.  There criteria were selected
        based on the workflow of the consumer portal.  Based on that workflow, the 6 pieces of info can only
        have been gathered if it is a refinance for a primary residence and the ssn has been collected.
        Opted for this method, rather than check for the 6 pieces of information direclty, since poor data
        modeling makes it hard to verify whether the borrower's address has been gathered.
        """
        can_trigger = self.can_trigger_respa_for_consumer_portal()
        if can_trigger:
            self.trigger_respa()
        return can_trigger

    def trigger_respa_for_advisor_portal(self):
        """
        Trigger respa for advisor portal if criteria were selected
        based on the workflow of the advisor portal.
        """
        can_trigger = self.can_trigger_respa_for_advisor_portal()
        if can_trigger:
            self.trigger_respa()
        return can_trigger

    def trigger_respa(self):
        """
        USE WITH CAUTION - this method will always trigger respa, whether or not we actually have the data
        in our data model.  This is necessary for situations where the advisor might want to trigger respa
        from the advisor portal; for example, because they have collected the remaining info verbally.

        note: only sets respa_triggered to true if it is not already true; this prevents the respa_triggered_at
        field from being reset to a later time.  the respa 72 hour window cannot be "restarted".
        """
        if self.respa_triggered is False:
            self._respa_triggered = True
            self.save()

    @property
    def respa_triggered(self):
        return self._respa_triggered

    ########################
    # prequal letter stuff #
    ########################
    # Should only have to include `TX` but we have some bad data in prod...
    PREQUAL_LETTER_NOT_ALLOWED_STATES = ['TX']

    # DOWNLOAD PREQUAL LETTER
    def permitted_state_for_prequal_letter(self):
        mp = self.current_mortgage_profile
        if (mp is None) or (mp.property_state_code is None):
            return None
        return self.current_mortgage_profile.property_state_code not in self.PREQUAL_LETTER_NOT_ALLOWED_STATES

    def view_prequal_criteria(self):
        return {
            'is_prequalified': self.is_prequalified(),
            'permitted_state_for_prequal_letter': self.permitted_state_for_prequal_letter(),
        }

    def can_view_prequal(self, raise_exception=False):
        criteria = self.view_prequal_criteria()
        can_view = all((criteria.values()))
        if not can_view and raise_exception:
            errors = ['all criteria must be true', {'criteria': criteria}]
            raise exceptions.ValidationError({'errors': errors})
        return can_view

    # SEND REALTOR EMAIL
    def send_realtor_prequal_criteria(self):
        return {
            'is_purchase': self.is_purchase(),
            'is_prequalified': self.is_prequalified(),
            'permitted_state_for_prequal_letter': self.permitted_state_for_prequal_letter(),
        }

    def can_send_realtor_prequal(self, raise_exception=False):
        criteria = self.send_realtor_prequal_criteria()
        can_send = all((criteria.values()))
        if not can_send and raise_exception:
            errors = ['all criteria must be true', {'criteria': criteria}]
            raise exceptions.ValidationError({'errors': errors})
        return can_send


@python_2_unicode_compatible
class LoanV1(TimeStampedModel):
    """A loan entry"""
    is_active = models.BooleanField(default=True)
    # blank and null set to True in debugging purpose.
    loan_id = models.CharField(max_length=255, blank=True)
    loan_profile = models.OneToOneField(LoanProfileV1, blank=True, null=True)

    property_address = models.ForeignKey('AddressV1', related_name='+',
                                         on_delete=models.SET_NULL, null=True, blank=True)

    lock_date = models.DateField(blank=True, null=True)
    lock_days = models.PositiveIntegerField(blank=True, null=True)
    lender_name = models.CharField(max_length=255, blank=True)
    product = models.CharField(max_length=255, blank=True)
    loan_amount = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                             max_digits=10, decimal_places=2, default=None)

    # Future use. Not money.
    ltv = models.CharField(max_length=255, blank=True)

    # Interest should be a numeric field of some type. Check.
    interest_rate = models.CharField(max_length=255, blank=True)
    purchase_price = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY, max_digits=10,
                                decimal_places=2, default=None)
    monthly_principal_and_interest = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY, max_digits=10,
                                                decimal_places=2, default=None)
    total_monthly_payment = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY, max_digits=10,
                                       decimal_places=2, default=None)
    target_close_date = models.DateField(null=True, blank=True)

    last_sync = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return self.loan_id


@python_2_unicode_compatible
class sampleTeamV1(TimeStampedModel):
    loan = models.ForeignKey('LoanV1', related_name='sample_team')

    coordinator = models.ForeignKey('accounts.Coordinator', related_name='loans', blank=True, null=True)
    specialist = models.ForeignKey('accounts.Specialist', related_name='loans', blank=True, null=True)
    realtor = models.ForeignKey('accounts.Realtor', related_name='loans', null=True, blank=True)
    processor = models.ForeignKey('ContactV1', null=True, related_name='+')
    escrow_officer = models.ForeignKey('ContactV1', null=True, related_name='+')
    title_officer = models.ForeignKey('ContactV1', null=True, related_name='+')

    # pylint: disable=R0201
    def __str__(self):
        return 'sample Team'


class Lead(TimeStampedModel):
    name = models.CharField(max_length=255)
    lead_id = models.CharField(max_length=255)


class EmploymentV1(TimeStampedModel):
    """Borrower and coborrower employment"""
    # Company
    s_corp_percent = models.IntegerField(blank=True, null=True,
                                         validators=[MinValueValidator(0), MaxValueValidator(100)])
    c_corp_percent = models.IntegerField(blank=True, null=True,
                                         validators=[MinValueValidator(0), MaxValueValidator(100)])
    company_entity_type = models.CharField(max_length=50, blank=True)
    company_other_entity_type = models.CharField(max_length=50, blank=True)
    company_address = models.ForeignKey('AddressV1', related_name='%(class)s_company_address', null=True, blank=True,
                                        on_delete=models.SET_NULL)
    company_name = models.CharField(blank=True, null=True, max_length=64)
    # Individual
    phone = models.CharField(blank=True, null=True, max_length=64)
    phone_extension = models.CharField(blank=True, null=True, max_length=64)
    title = models.CharField(blank=True, null=True, max_length=64)
    address = models.ForeignKey('AddressV1', related_name='%(class)s_address', null=True, blank=True,
                                on_delete=models.SET_NULL)
    start_date = models.DateField(null=True, blank=True,
                                  validators=[MinValueValidator(EncompassConfig.MIN_DATE),
                                              MaxValueValidator(EncompassConfig.MAX_DATE)])
    end_date = models.DateField(null=True, blank=True,
                                validators=[MinValueValidator(EncompassConfig.MIN_DATE),
                                            MaxValueValidator(EncompassConfig.MAX_DATE)])
    years_in_field = models.IntegerField(null=True, blank=True)
    is_employee_of_company = models.NullBooleanField()
    is_self_employed = models.NullBooleanField()
    is_current_employment = models.NullBooleanField()

    @property
    def months(self):
        return _get_years_months(self.start_date, self.end_date)[1]

    @property
    def years(self):
        return _get_years_months(self.start_date, self.end_date)[0]

    @property
    def full_phone(self):
        if self.phone:
            ext = self.phone_extension if self.phone_extension else ''
            phone_number = PHONE_RE.sub('', ''.join([self.phone, ext]))
        else:
            phone_number = self.phone
        return phone_number


class AddressV1(TimeStampedModel):
    """All addresses for every model"""
    street = models.CharField(blank=True, null=True, max_length=128)
    city = models.CharField(blank=True, null=True, max_length=128)
    state = models.CharField(blank=True, null=True, max_length=64)
    postal_code = models.CharField(blank=True, null=True, max_length=16)
    country = models.CharField(max_length=100, default='United States of America')
    start_date = models.DateField(null=True, blank=True,
                                  validators=[MinValueValidator(EncompassConfig.MIN_DATE),
                                              MaxValueValidator(EncompassConfig.MAX_DATE)])
    end_date = models.DateField(null=True, blank=True,
                                validators=[MinValueValidator(EncompassConfig.MIN_DATE),
                                            MaxValueValidator(EncompassConfig.MAX_DATE)])
    rent_or_own = models.NullBooleanField()

    class Meta:
        ordering = ('created',)

    def is_mismo_complete(self):
        ''' Is there content for the primary address fields '''
        return all([self.street, self.city, self.state, self.postal_code])

    @property
    def months(self):
        return _get_years_months(self.start_date, self.end_date)[1]

    @property
    def years(self):
        return _get_years_months(self.start_date, self.end_date)[0]

    @months.setter
    def months(self, months):
        current_years = self.years if self.years else 0
        self.end_date = datetime.datetime.today()
        self.start_date = self.end_date - relativedelta(years=current_years, months=months)

    @years.setter
    def years(self, years):
        current_months = self.months if self.months else 0
        self.end_date = datetime.datetime.today()
        self.start_date = self.end_date - relativedelta(years=years, months=current_months)

    def __str__(self):
        # pylint: disable=missing-format-attribute
        return '{0.street}, {0.state} {0.postal_code} (id: {0.id})'.format(self)


class ContactV1(TimeStampedModel):
    """Person or company contact data"""
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    address = models.ForeignKey('AddressV1', related_name='+', null=True, blank=True,
                                on_delete=models.SET_NULL)
    email = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255, blank=True)

    @property
    def username(self):
        return '{} {}'.format(self.first_name, self.last_name)

    @username.setter
    def username(self, name):
        name_parts = name.split(None, 1)
        self.first_name = name_parts[0]
        self.last_name = name_parts[1] if 1 < len(name_parts) else ''


@python_2_unicode_compatible
class BorrowerBaseV1(TimeStampedModel):
    class Meta:
        abstract = True

    # XXXrex: add to marital_status and citizenship_status field as choices to advisor portal
    # need to check does not break advisor portal serializers
    # single and divorced are not valid MISMO marital_status
    MARITAL_STATUS_CHOICES = Choices('married', 'separated', 'unmarried', 'single', 'divorced')
    JOB_STATUS_CHOICES = Choices(
        ('employed', 'Full-Time'),
        ('self_employed', 'Self-Employed'),
        ('retired', 'Retired'),
        ('other', 'Other'),
    )

    CITIZENSHIP_STATUS_CHOICES = Choices(
        'us_citizen',
        'permanent_resident_alien',
        'foreign_national',
        'non_permanent_resident_alien',
        'other',
    )

    sample_TO_MISMO_CITIZENSHIP_RESIDENCY = {
        CITIZENSHIP_STATUS_CHOICES.us_citizen: 'USCitizen',
        CITIZENSHIP_STATUS_CHOICES.permanent_resident_alien: 'PermanentResidentAlien',
        CITIZENSHIP_STATUS_CHOICES.non_permanent_resident_alien: 'NonPermanentResidentAlien',
        CITIZENSHIP_STATUS_CHOICES.foreign_national: 'NonResidentAlien',
        CITIZENSHIP_STATUS_CHOICES.other: 'Unknown',
    }

    MISMO_TO_sample_CITIZENSHIP_STATUS = {value: key for key, value in sample_TO_MISMO_CITIZENSHIP_RESIDENCY.items()}

    is_active = models.BooleanField(default=True)

    ssn = TextPGPPublicKeyField(blank=True, null=True)
    dob = models.DateField(null=True, blank=True,
                           validators=[MinValueValidator(EncompassConfig.MIN_DATE),
                                       MaxValueValidator(EncompassConfig.MAX_DATE)])
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(blank=True, null=True, max_length=128)
    middle_name = models.CharField(blank=True, null=True, max_length=128)
    last_name = models.CharField(blank=True, null=True, max_length=128)
    name_suffix = models.CharField(blank=True, null=True, max_length=20)
    # How name should appear on documents
    title_name = models.CharField(blank=True, null=True, max_length=128)
    home_phone = models.CharField(blank=True, null=True, max_length=64)
    role = models.CharField(max_length=50, blank=True)

    rent_or_own = models.NullBooleanField()

    # Comma-separated field
    has_dependents_ages = models.NullBooleanField()
    dependents_ages = models.CharField(max_length=100, blank=True)
    marital_status = models.CharField(blank=True, null=True, max_length=16)  # BORROWER/@MaritalStatusType
    citizenship_status = models.CharField(max_length=100, blank=True)
    years_in_school = models.PositiveIntegerField(blank=True, null=True)
    has_been_student_in_last_two_years = models.NullBooleanField()

    _job_status = models.CharField(choices=JOB_STATUS_CHOICES, max_length=100, blank=True)
    is_retired = models.NullBooleanField()  # no equivalent field in MISMO 2.3.1
    is_self_employed = models.NullBooleanField()  # BORROWER/EMPLOYER/@EmploymentBorrowerSelfEmployedIndicator Y,N
    has_additional_property = models.NullBooleanField()
    is_purchase_first_time_buyer = models.NullBooleanField()

    is_veteran = models.NullBooleanField()
    is_first_va_loan = models.NullBooleanField()
    receives_va_disability = models.NullBooleanField()
    service_branch = models.CharField(max_length=100, blank=True)
    current_service_status = models.CharField(max_length=100, blank=True)
    years_in_service = models.IntegerField(blank=True, null=True)
    has_additional_income_sources = models.NullBooleanField()
    is_mailing_address_same = models.NullBooleanField(default=True)
    referral = models.CharField(max_length=100, blank=True)
    employment_gap_explanation = models.TextField(blank=True, null=True)
    housing_gap_explanation = models.TextField(blank=True, null=True)

    use_escrow_for_insurance = models.NullBooleanField()
    use_escrow_for_property_taxes = models.NullBooleanField()

    # TRANSMITTAL_DATA/@CreditReportAuthorizationIndicator (Y|N)
    is_credit_report_authorized = models.NullBooleanField()
    is_credit_report_authorized_updated = MonitorField(monitor='is_credit_report_authorized',
                                                       null=True, default=None)

    # Relationships
    mailing_address = models.ForeignKey('AddressV1', related_name='%(class)s_mailing_address', null=True, blank=True,
                                        on_delete=models.SET_NULL)
    demographics = models.ForeignKey('DemographicsV1', related_name='%(class)s', null=True, blank=True,
                                     on_delete=models.SET_NULL)
    realtor = models.ForeignKey('ContactV1', null=True, related_name='%(class)s_realtor',
                                on_delete=models.SET_NULL)

    previous_addresses = models.ManyToManyField('AddressV1', related_name='%(class)s')
    previous_employment = models.ManyToManyField('EmploymentV1', related_name='%(class)s')
    holding_assets = models.ManyToManyField('HoldingAssetV1', related_name='%(class)s')
    vehicle_assets = models.ManyToManyField('VehicleAssetV1', related_name='%(class)s')
    insurance_assets = models.ManyToManyField('InsuranceAssetV1', related_name='%(class)s')
    income = models.ManyToManyField('IncomeV1', related_name='%(class)s')
    expense = models.ManyToManyField('ExpenseV1', related_name='%(class)s')
    liabilities = models.ManyToManyField('LiabilityV1', related_name='%(class)s')

    objects = PGPEncryptedManager()

    @property
    def dependents_count(self):
        if self.has_dependents_ages is None:
            retval = None
        elif self.has_dependents_ages:
            retval = len(self.dependents_ages.split(',')) if self.dependents_ages else 0
        else:
            retval = 0
        return retval

    @property
    def dependents_ages_parsed(self):
        if self.has_dependents_ages is None:
            retval = None
        elif self.has_dependents_ages:
            retval = self.dependents_ages
        else:
            retval = ''
        return retval

    @property
    def full_name(self):
        """Convenience property"""
        return '{0.first_name} {0.last_name}'.format(self)

    @property
    def username(self):
        """Convenience property for compatibility with accounts.User"""
        return '{0.first_name} {0.last_name}'.format(self)

    @property
    def address(self):
        return self.previous_addresses.exclude(end_date__isnull=True).order_by('-end_date').first()

    @property
    def employment(self):
        return (self.previous_employment.latest('end_date')
                if self.previous_employment.exists()
                else None)

    @property
    def mismo_citizenship_residency(self):
        return self.sample_TO_MISMO_CITIZENSHIP_RESIDENCY.get(self.citizenship_status)

    @property
    def mismo_ssn(self):
        assert re.match(r'[0-9]{3}-[0-9]{2}-[0-9]{4}', self.ssn), 'ssn in unexpected format: {0}'.format(self.ssn)
        return self.ssn.replace('-', '')

    @classmethod
    def mismo_to_sample_citizenship_status(cls, status):
        return cls.MISMO_TO_sample_CITIZENSHIP_STATUS.get(status)

    # Properties for the customer_portal
    @property
    def job_status(self):
        return self._job_status

    # pylint: disable=function-redefined
    @job_status.setter
    def job_status(self, job_status):
        """
        This field will be changed by the customer through the customer_portal.
        The advisor portal, for now, will not be able to change this field and instead
        will make edits directly to:
            is_self_employed
            is_retired

        Therefore, the below logic ensures setting _job_status has the necessary side effects
        to surface the appropriate information in the advisor portal
        """
        self._job_status = job_status
        if job_status == self.JOB_STATUS_CHOICES.employed:
            self.is_self_employed = None
            self.is_retired = None
        elif job_status == self.JOB_STATUS_CHOICES.self_employed:
            self.is_self_employed = True
            self.is_retired = None
        elif job_status == self.JOB_STATUS_CHOICES.retired:
            self.is_self_employed = None
            self.is_retired = True
        elif job_status == self.JOB_STATUS_CHOICES.other:
            self.is_self_employed = None
            self.is_retired = None
        else:
            self.is_self_employed = None
            self.is_retired = None
            self._job_status = None
        return self._job_status

    def get_current_residence(self):
        """
        note: this method is also provided for the coborrower to handle situations
        where cob.living_together_two_years is True
        """
        return self.address

    def get_previous_residences(self):
        """
        note: this method is also provided for the coborrower to handle situations
        where cob.living_together_two_years is True
        """
        return self.previous_addresses.order_by('-start_date')

    @property
    def years_of_residence_history(self):
        addresses = self.get_previous_residences()
        return sum([(addr.years + addr.months / 12.0) for addr in addresses
                    if addr.years is not None and addr.months is not None])

    def __str__(self):
        return self.full_name


class BorrowerV1(BorrowerBaseV1):
    loan_profile = models.ForeignKey('LoanProfileV1', related_name='borrowers')

    current_property_type = models.CharField(max_length=50, blank=True)
    is_current_property_owner = models.NullBooleanField()
    is_current_property_second_or_rental = models.NullBooleanField()
    is_current_property_plans_to_sell = models.NullBooleanField()
    is_current_property_in_contract = models.NullBooleanField()
    will_current_property_sold_by_close = models.NullBooleanField()
    # For distinguishing primary borrower
    ordering = models.IntegerField(blank=True, null=True)

    # added for customer_portal
    properties_owned_count = models.PositiveIntegerField(null=True)

    @property
    def owns_multiple_properties(self):
        return None if (self.properties_owned_count is None) else (self.properties_owned_count > 1)

    def has_active_coborrower(self):
        return hasattr(self, 'coborrower') and self.coborrower.is_active

    def get_active_coborrower(self):
        coborrower = getattr(self, 'coborrower', None)
        return coborrower if coborrower is not None and coborrower.is_active else None

    def get_access_code_signature(self):
        access_code_signature = {'lp_guid': str(self.loan_profile.guid)}
        return access_code_signature

    def get_base_income_with_not_empty_value(self):
        return self.income.filter(kind=IncomeV1.BASE, value__isnull=False).first()


class CoborrowerV1(BorrowerBaseV1):
    borrower = models.OneToOneField('BorrowerV1', null=False, related_name='coborrower')
    living_together_two_years = models.NullBooleanField()

    @property
    def loan_profile(self):
        return self.borrower.loan_profile

    def get_current_residence(self):
        return (self.borrower.get_current_residence() if self.living_together_two_years else
                self.address)

    def get_previous_residences(self):
        return (self.borrower.get_previous_residences() if self.living_together_two_years else
                self.previous_addresses.order_by('-start_date'))


class HoldingAssetV1(TimeStampedModel):
    # Mismo 2.3.1 ASSET/@_Type
    AUTOMOBILE = 'automobile'
    BOND = 'bond'
    BRIDGE_LOAN_NOT_DEPOSITED = 'bridge_loan_not_deposited'
    CASH_ON_HAND = 'cash_on_hand'
    CERTIFICATE_OF_DEPOSIT_TIME_DEPOSIT = 'certificate_of_deposit_time_deposit'
    CHECKING_ACCOUNT = 'checking_account'
    EARNEST_MONEY_CASH_DEPOSIT_TOWARD_PURCHASE = 'earnest_money_cash_deposit_toward_purchase'
    GIFTS_TOTAL = 'gifts_total'
    GIFTS_NOT_DEPOSITED = 'gifts_not_deposited'
    LIFE_INSURANCE = 'life_insurance'
    MONEY_MARKET_FUND = 'money_market_fund'
    MUTUAL_FUND = 'mutual_fund'
    NET_WORTH_OF_BUSINESS_OWNED = 'net_worth_of_business_owned'
    OTHER_LIQUID_ASSETS = 'other_liquid_assets'
    OTHER_NON_LIQUID_ASSETS = 'other_non_liquid_assets'
    PENDING_NET_SALE_PROCEEDS_FROM_REAL_ESTATE_ASSETS = 'pending_net_sale_proceeds_from_real_estate_assets'
    RELOCATION_MONEY = 'relocation_money'
    RETIREMENT_FUND = 'retirement_fund'
    SALE_OTHER_ASSETS = 'sale_other_assets'
    SAVINGS_ACCOUNT = 'savings_account'
    SECURED_BORROWED_FUNDS_NOT_DEPOSITED = 'secured_borrowed_funds_not_deposited'
    STOCK = 'stock'
    TRUST_ACCOUNT = 'trust_account'
    MISMO_KINDS = (AUTOMOBILE, BOND, BRIDGE_LOAN_NOT_DEPOSITED, CASH_ON_HAND, CERTIFICATE_OF_DEPOSIT_TIME_DEPOSIT,
                   CHECKING_ACCOUNT, EARNEST_MONEY_CASH_DEPOSIT_TOWARD_PURCHASE, GIFTS_TOTAL, GIFTS_NOT_DEPOSITED,
                   LIFE_INSURANCE, MONEY_MARKET_FUND, MUTUAL_FUND, NET_WORTH_OF_BUSINESS_OWNED, OTHER_LIQUID_ASSETS,
                   OTHER_NON_LIQUID_ASSETS, PENDING_NET_SALE_PROCEEDS_FROM_REAL_ESTATE_ASSETS, RELOCATION_MONEY,
                   RETIREMENT_FUND, SALE_OTHER_ASSETS, SAVINGS_ACCOUNT, SECURED_BORROWED_FUNDS_NOT_DEPOSITED, STOCK,
                   TRUST_ACCOUNT,)

    # Fannie Mismo 2.3.1 extra ASSET/@_Type's
    GIFT_OF_EQUITY = 'gift_of_equity'
    FANNIE_KINDS = MISMO_KINDS + (GIFT_OF_EQUITY,)

    # Mortgage Advisor Portal kinds, these should be removed eventually
    MAP_CHECKING = 'checking'
    MAP_SAVINGS = 'savings'
    MAP_MONEY_MARKET = 'money_market'
    MAP_CERTIFICATE_OF_DEPOSIT = 'certificate_of_deposit'
    MAP_CASH_MANAGEMENT_ACCOUNT = 'cash_management_account'
    MAP_TRUST = 'trust'
    MAP_401K = '401k'
    MAP_INVESTMENT = 'investment'
    MAP_INSURANCE = 'insurance'
    MAP_INVESTMENT_BROKERAGE = 'investment_brokerage'
    MAP_KINDS = (MAP_CHECKING, MAP_SAVINGS, MAP_MONEY_MARKET, MAP_CERTIFICATE_OF_DEPOSIT, MAP_CASH_MANAGEMENT_ACCOUNT,
                 MAP_TRUST, MAP_401K, MAP_INVESTMENT, MAP_INSURANCE, MAP_INVESTMENT_BROKERAGE,)

    _sample_TO_MISMO_ASSET_KIND = {
        AUTOMOBILE: 'Automobile',
        BOND: 'Bond',
        BRIDGE_LOAN_NOT_DEPOSITED: 'BridgeLoanNotDeposited',
        CASH_ON_HAND: 'CashOnHand',
        CERTIFICATE_OF_DEPOSIT_TIME_DEPOSIT: 'CertificateOfDepositTimeDeposit',
        CHECKING_ACCOUNT: 'CheckingAccount',
        EARNEST_MONEY_CASH_DEPOSIT_TOWARD_PURCHASE: 'EarnestMoneyCashDepositTowardPurchase',
        GIFTS_TOTAL: 'GiftsTotal',
        GIFTS_NOT_DEPOSITED: 'GiftsNotDeposited',
        LIFE_INSURANCE: 'LifeInsurance',
        MONEY_MARKET_FUND: 'MoneyMarketFund',
        MUTUAL_FUND: 'MutualFund',
        NET_WORTH_OF_BUSINESS_OWNED: 'NetWorthOfBusinessOwned',
        OTHER_LIQUID_ASSETS: 'OtherLiquidAssets',
        OTHER_NON_LIQUID_ASSETS: 'OtherNonLiquidAssets',
        PENDING_NET_SALE_PROCEEDS_FROM_REAL_ESTATE_ASSETS: 'PendingNetSaleProceedsFromRealEstateAssets',
        RELOCATION_MONEY: 'RelocationMoney',
        RETIREMENT_FUND: 'RetirementFund',
        SALE_OTHER_ASSETS: 'SaleOtherAssets',
        SAVINGS_ACCOUNT: 'SavingsAccount',
        SECURED_BORROWED_FUNDS_NOT_DEPOSITED: 'SecuredBorrowedFundsNotDeposited',
        STOCK: 'Stock',
        TRUST_ACCOUNT: 'TrustAccount',
        # fannie only
        GIFT_OF_EQUITY: 'GiftOfEquity',
    }

    sample_TO_MISMO_ASSET_KIND = _sample_TO_MISMO_ASSET_KIND.copy()
    sample_TO_MISMO_ASSET_KIND.update({
        MAP_CHECKING: CHECKING_ACCOUNT,
        MAP_SAVINGS: SAVINGS_ACCOUNT,
        MAP_MONEY_MARKET: MONEY_MARKET_FUND,
        MAP_CERTIFICATE_OF_DEPOSIT: CERTIFICATE_OF_DEPOSIT_TIME_DEPOSIT,
        MAP_CASH_MANAGEMENT_ACCOUNT: CHECKING_ACCOUNT,
        MAP_TRUST: TRUST_ACCOUNT,
        MAP_401K: RETIREMENT_FUND,
        MAP_INVESTMENT: STOCK,
        MAP_INSURANCE: LIFE_INSURANCE,
        MAP_INVESTMENT_BROKERAGE: STOCK,
    })

    # use _sample... instead of sample... to avoid mapping a MISMO kind to a MAP kind
    MISMO_TO_sample_ASSET_KIND = {value: key for key, value in _sample_TO_MISMO_ASSET_KIND.items()}

    name = models.CharField(blank=True, null=True, max_length=128)
    description = models.CharField(blank=True, null=True, max_length=128)
    account_number = TextPGPPublicKeyField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    symbol = models.CharField(max_length=255, blank=True)
    cusip = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=255, blank=True)
    current_value = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                               max_digits=10, decimal_places=2, default=None)
    institution_name = models.CharField(max_length=255, blank=True)
    institution_address = models.ForeignKey('AddressV1', related_name='%(class)s_institution_address', null=True,
                                            blank=True, on_delete=models.SET_NULL)
    is_liquidating_or_borrowing = models.NullBooleanField()

    objects = PGPEncryptedManager()

    @property
    def mismo_kind(self):
        return self.sample_TO_MISMO_ASSET_KIND.get(self.kind)

    @classmethod
    def mismo_to_sample_kind(cls, kind):
        return cls.MISMO_TO_sample_ASSET_KIND.get(kind)

    @property
    def encompass_description(self):
        return '{0.institution_name} {0.account_number}'.format(self)

    @property
    def encompass_owner(self):
        return {(True, True): 'Both',
                (True, False): 'Borrower',
                (False, True): 'CoBorrower',
                (False, False): None}[(self.borrowerv1.filter(is_active__exact=True).exists(),
                                       self.coborrowerv1.filter(is_active__exact=True).exists())]

    def __str__(self):
        return '{0} {1}'.format(self.kind, str(self.current_value))


class VehicleAssetV1(TimeStampedModel):
    make = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    year = models.CharField(max_length=255, blank=True)
    value = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                       max_digits=10, decimal_places=2, default=None)

    @property
    def encompass_description(self):
        return '{0.make} {0.year}'.format(self)


class InsuranceAssetV1(TimeStampedModel):
    LIFE = 'Life Insurance'
    OTHER = 'Other'

    INSURANCE_CHOICES = (
        (LIFE, LIFE),
        (OTHER, OTHER)
    )

    kind = models.CharField(choices=INSURANCE_CHOICES, max_length=100, blank=True)
    name = models.CharField(max_length=255, blank=True)
    value = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                       max_digits=10, decimal_places=2, default=None)

    def __str__(self):
        return '{0} {1} {2}'.format(self.kind, self.name, str(self.value if self.value else '0.00'))


class IncomeV1(TimeStampedModel):
    BASE = 'Base'
    BONUS = 'Bonus'
    COMMISSION = 'Commission'
    DIVIDEND = 'Dividend'
    NET_RENTAL = 'Net Rental'
    OTHER = 'Other'
    OVERTIME = 'Overtime'

    DEFAULT_KIND = OTHER

    INCOME_CHOICES = (
        (BASE, BASE),
        (BONUS, BONUS),
        (COMMISSION, COMMISSION),
        (DIVIDEND, DIVIDEND),
        (NET_RENTAL, NET_RENTAL),
        (OTHER, OTHER),
        (OVERTIME, OVERTIME),
    )

    sample_TO_MISMO_INCOME_KIND = {
        BASE: 'Base',
        BONUS: 'Bonus',
        COMMISSION: 'Commissions',
        DIVIDEND: 'DividendsInterest',
        NET_RENTAL: 'NetRentalIncome',
        OTHER: 'OtherTypesOfIncome',
        OVERTIME: 'Overtime',
    }

    MISMO_TO_sample_INCOME_KIND = {value: key for key, value in sample_TO_MISMO_INCOME_KIND.items()}

    kind = models.CharField(max_length=100, choices=INCOME_CHOICES)
    name = models.CharField(max_length=255, blank=True)
    value = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                       max_digits=10, decimal_places=2, default=None)
    description = models.CharField(max_length=255, blank=True)
    use_automated_process = models.NullBooleanField()

    @property
    def mismo_kind(self):
        return self.sample_TO_MISMO_INCOME_KIND.get(self.kind)

    @classmethod
    def sample_to_mismo_kind(cls, kind):
        return cls.MISMO_TO_sample_INCOME_KIND.get(kind, cls.DEFAULT_KIND)

    def __str__(self):
        return '{0} {1}'.format(self.kind, str(self.value if self.value else '0.00'))


class ExpenseV1(TimeStampedModel):
    FIRST_MORTGAGE = 'First Mortgage'
    HAZARD_INSURANCE = 'Hazard Insurance'
    HOA = 'Homeowner Association'
    MORTGAGE_INSURANCE = 'Mortgage Insurance'
    OTHER = 'Other'
    OTHER_FINANCING = 'Other Financing'
    REAL_ESTATE = 'Real Estate'
    RENT = 'Rent'

    EXPENSE_CHOICES = (
        (RENT, RENT),
        (FIRST_MORTGAGE, FIRST_MORTGAGE),
        (OTHER_FINANCING, OTHER_FINANCING),
        (REAL_ESTATE, REAL_ESTATE),
        (MORTGAGE_INSURANCE, MORTGAGE_INSURANCE),
        (HAZARD_INSURANCE, HAZARD_INSURANCE),
        (HOA, HOA),
        (OTHER, OTHER)
    )

    sample_TO_MISMO_EXPENSE_KIND = {
        FIRST_MORTGAGE: 'FirstMortgagePrincipalAndInterest',
        HAZARD_INSURANCE: 'HazardInsurance',
        HOA: 'HomeownersAssociationDuesAndCondominiumFees',
        MORTGAGE_INSURANCE: 'MI',
        OTHER: 'OtherMortgageLoanPrincipalAndInterest',
        OTHER_FINANCING: 'OtherHousingExpense',
        REAL_ESTATE: 'RealEstateTax',
        RENT: 'Rent',
    }

    MISMO_TO_sample_EXPENSE_KIND = {value: key for key, value in sample_TO_MISMO_EXPENSE_KIND.items()}

    kind = models.CharField(max_length=100, choices=EXPENSE_CHOICES)
    value = MoneyField(blank=True, null=True, default_currency=DEFAULT_CURRENCY,
                       max_digits=10, decimal_places=2, default=None)
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)

    @property
    def mismo_kind(self):
        return self.sample_TO_MISMO_EXPENSE_KIND.get(self.kind)

    @classmethod
    def mismo_to_sample_kind(cls, expense_kind):
        return cls.MISMO_TO_sample_EXPENSE_KIND.get(expense_kind)

    def __str__(self):
        return '{0} {1}'.format(self.kind, str(self.value if self.value else '0.00'))


class LiabilityV1(TimeStampedModel):
    # Kind
    CHILD_CARE = 'child_care'
    CHILD_SUPPORT = 'child_support'
    COLLECTIONS_JUDGMENTS_AND_LIENS = 'collections_judgments_and_liens'
    HELOC = 'heloc'
    INSTALLMENT = 'installment'
    LEASE_PAYMENTS = 'lease_payments'
    MORTGAGE_LOAN = 'mortgage_loan'
    OPEN_30_DAYS_CHARGE_ACCOUNT = 'open_30_days_charge_account'
    OTHER_EXPENSE = 'other_expense'
    OTHER_LIABILITY = 'other_liability'
    REVOLVING = 'revolving'
    SEPARATE_MAINTENANCE_EXPENSE = 'separate_maintenance_expense'
    TAXES = 'taxes'

    # Source
    ADVISOR_QUESTIONNAIRE = 'advisor_questionnaire'
    CBC_CREDIT_REPORT = 'cbc_credit_report'
    CONSUMER_QUESTIONNAIRE = 'consumer_questionnaire'

    LIABILITY_KIND_CHOICES = (
        (CHILD_CARE, 'Child Care'),
        (CHILD_SUPPORT, 'Child Support'),
        (COLLECTIONS_JUDGMENTS_AND_LIENS, 'Collections Judgments And Liens'),
        (HELOC, 'HELOC'),
        (INSTALLMENT, 'Installment'),
        (LEASE_PAYMENTS, 'Lease Payments'),
        (MORTGAGE_LOAN, 'Mortgage Loan'),
        (OPEN_30_DAYS_CHARGE_ACCOUNT, 'Open 30 Days Charge Account'),
        (OTHER_EXPENSE, 'Other Expense'),
        (OTHER_LIABILITY, 'Other Liability'),
        (REVOLVING, 'Revolving'),
        (SEPARATE_MAINTENANCE_EXPENSE, 'Separate Maintenance Expense'),
        (TAXES, 'Taxes'),
    )

    sample_TO_MISMO_LIABILITY_KIND = {
        CHILD_CARE: 'ChildCare',
        CHILD_SUPPORT: 'ChildSupport',
        COLLECTIONS_JUDGMENTS_AND_LIENS: 'CollectionsJudgementsAndLiens',
        HELOC: 'HELOC',
        INSTALLMENT: 'Installment',
        LEASE_PAYMENTS: 'LeasePayments',
        MORTGAGE_LOAN: 'MortgageLoan',
        OPEN_30_DAYS_CHARGE_ACCOUNT: 'Open30DayChargeAccount',
        OTHER_EXPENSE: 'OtherExpense',
        OTHER_LIABILITY: 'OtherLiability',
        REVOLVING: 'Revolving',
        SEPARATE_MAINTENANCE_EXPENSE: 'SeparateMaintenanceExpense',
        TAXES: 'Taxes',
    }

    MISMO_TO_sample_LIABILITY_KIND = {value: key for key, value in sample_TO_MISMO_LIABILITY_KIND.items()}

    LIABILITY_SOURCE_CHOICES = (
        (ADVISOR_QUESTIONNAIRE, 'Advisor Questionnaire'),
        (CBC_CREDIT_REPORT, 'CBC Credit Report'),
        (CONSUMER_QUESTIONNAIRE, 'Consoumer Questionnaire'),
    )

    kind = models.CharField(max_length=50, blank=True, choices=LIABILITY_KIND_CHOICES)
    source = models.CharField(
        max_length=50, blank=True, choices=LIABILITY_SOURCE_CHOICES,
        default=ADVISOR_QUESTIONNAIRE)
    holder_name = models.CharField(max_length=255, blank=True)
    holder_address = models.ForeignKey(
        'AddressV1', related_name='%(class)s_holder_address', null=True,
        blank=True, on_delete=models.SET_NULL)
    account_in_name_of = models.CharField(max_length=255, blank=True)
    account_identifier = TextPGPPublicKeyField(blank=True, null=True)
    monthly_payment = MoneyField(
        blank=True, null=True, default_currency=DEFAULT_CURRENCY,
        max_digits=10, decimal_places=2, default=None)
    months_remaining = models.IntegerField(blank=True, null=True)
    unpaid_balance = MoneyField(
        blank=True, null=True, default_currency=DEFAULT_CURRENCY,
        max_digits=10, decimal_places=2, default=None)
    exclude_from_liabilities = models.NullBooleanField()
    will_be_paid_off = models.NullBooleanField()
    will_be_subordinated = models.NullBooleanField()
    # for alimony and job_related_expense kinds
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    comment_updated = models.DateTimeField(blank=True, null=True)

    # For API usage
    # Liabilities imported from the credit report have some edit restrictions
    is_editable = models.BooleanField(default=True)

    @property
    def encompass_owner(self):
        return {(True, True): 'Both',
                (True, False): 'Borrower',
                (False, True): 'CoBorrower',
                (False, False): None}[(self.borrowerv1.filter(is_active__exact=True).exists(),
                                       self.coborrowerv1.filter(is_active__exact=True).exists())]

    @property
    def mismo_kind(self):
        return self.sample_TO_MISMO_LIABILITY_KIND.get(self.kind)

    @classmethod
    def sample_to_mismo_kind(cls, kind):
        return cls.MISMO_TO_sample_LIABILITY_KIND.get(kind)

    objects = PGPEncryptedManager()

    def __str__(self):
        return '{0}, {1}'.format(self.kind, self.holder_name)


class DemographicsV1(TimeStampedModel):
    OWNED_PROPERTY_TYPE_CHOICES = ('PR', 'SH', 'IP')
    OWNED_PROPERTY_TITLE_HELD = ('S', 'SP', 'O')

    NOT_PROVIDED = 'InformationNotProvidedByApplicantInMailInternetOrTelephoneApplication'
    NOT_APPLICABLE = 'NotApplicable'

    # Ethnicity
    sample_TO_MISMO_ETHNICITY = {
        'hispanic_or_latino': 'HispanicOrLatino',
        'not_hispanic_or_latino': 'NotHispanicOrLatino',
    }

    MISMO_TO_sample_ETHNICITY = {value: key for key, value in sample_TO_MISMO_ETHNICITY.items()}

    # Race
    RACES = Choices(
        'AmericanIndianOrAlaskaNative',
        'Asian',
        'BlackOrAfricanAmerican',
        'NativeHawaiianOrOtherPacificIslander',
        'White',
        NOT_APPLICABLE,  # not surfaced in consumer_portal, but is an option in advisor_portal
        # NOT_PROVIDED is a valid choice per DTD, but not included since the property mismo_races surfaces it
    )

    # Gender
    sample_TO_MISMO_GENDER = {
        'male': 'Male',
        'female': 'Female',
    }

    MISMO_TO_sample_GENDER = {value: key for key, value in sample_TO_MISMO_GENDER.items()}

    # Fields
    ethnicity = models.CharField(blank=True, null=True, max_length=128)
    race = CustomArrayField(models.CharField(choices=RACES, blank=False, null=False, max_length=128),
                            null=False, blank=False, default=[])
    gender = models.CharField(blank=True, null=True, max_length=10)

    # borrower.citizenship_status is set in customer_portal
    # do not set is_us_citizen or is_permanent_resident_alien values directly.
    is_us_citizen = models.NullBooleanField()
    is_permanent_resident_alien = models.NullBooleanField()

    is_party_to_lawsuit = models.NullBooleanField()
    is_party_to_lawsuit_explanation = models.TextField(blank=True)
    is_obligated_to_pay_alimony_or_separate_maintenance = models.NullBooleanField()
    is_obligated_to_pay_alimony_or_separate_maintenance_explanation = models.TextField(blank=True)
    is_any_part_of_downpayment_borrowed = models.NullBooleanField()
    is_any_part_of_downpayment_borrowed_explanation = models.TextField(blank=True)
    is_comaker_or_endorser_on_note = models.NullBooleanField()
    is_comaker_or_endorser_on_note_explanation = models.TextField(blank=True)
    is_delinquent_on_debt_presently = models.NullBooleanField()
    is_delinquent_on_debt_presently_explanation = models.TextField(blank=True)
    has_outstanding_judgements = models.NullBooleanField()
    has_outstanding_judgements_explanation = models.TextField(blank=True)
    has_declared_bankruptcy_within_past_seven_years = models.NullBooleanField()
    has_declared_bankruptcy_within_past_seven_years_explanation = models.TextField(blank=True)
    has_property_foreclosed_within_past_seven_years = models.NullBooleanField()
    has_property_foreclosed_within_past_seven_years_explanation = models.TextField(blank=True)
    has_been_obligated_on_resulted_in_foreclosure_loan = models.NullBooleanField()
    has_been_obligated_on_resulted_in_foreclosure_loan_explanation = models.TextField(blank=True)

    has_ownership_interest_in_property_last_three_years = models.NullBooleanField()
    plans_to_occupy_as_primary_residence = models.NullBooleanField()
    are_ethnicity_questions_skipped = models.NullBooleanField()

    # For Declaration-M, not subject property
    owned_property_title_hold = models.CharField(max_length=50, blank=True)
    owned_property_type = models.CharField(max_length=50, blank=True)

    # TODO: for backwards-compatibility, need remove it later
    is_demographics_questions_request_confirmed = models.NullBooleanField()

    def _was_interview_face_to_face(self):
        coborrower = self.coborrowerv1.first()
        borrower = coborrower.borrower if coborrower else self.borrowerv1.first()
        return (borrower.loan_profile.application_taken_method ==
                LoanProfileV1.APPLICATION_TAKEN_METHOD_CHOICES.face_to_face)

    def get_borrower(self):
        borrowers = self.borrowerv1.all()
        if borrowers.count() > 1:
            logger.error('DEMOGRAPHICS-OBJ-HAS-MULTIPLE-BORROWERS id %s', self.id)
        return borrowers.first() if borrowers.exists() else None

    @property
    def mismo_races(self):
        return ([self.NOT_PROVIDED]
                if self.are_ethnicity_questions_skipped and not self._was_interview_face_to_face()
                else self.race)

    @property
    def mismo_ethnicity(self):
        return (self.NOT_PROVIDED
                if self.are_ethnicity_questions_skipped and not self._was_interview_face_to_face()
                else self.sample_TO_MISMO_ETHNICITY.get(self.ethnicity))

    @property
    def mismo_gender(self):
        return ('InformationNotProvidedUnknown'
                if self.are_ethnicity_questions_skipped and not self._was_interview_face_to_face()
                else self.sample_TO_MISMO_GENDER.get(self.gender))
