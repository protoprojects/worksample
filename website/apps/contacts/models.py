# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils.timezone import now
from django.db.models.query import QuerySet

from django_extensions.db.fields import UUIDField
from model_utils import Choices
from model_utils.managers import InheritanceManager

from core.models import TimeStampedModel
from accounts.models import Customer


MONDAY = "monday"
TUESDAY = "tuesday"
WEDNESDAY = "wednesday"
THURSDAY = "thursday"
FRIDAY = "friday"
SATURDAY = "saturday"
PREFFERED_DAY_CHOICES = (
    (MONDAY, "Monday"),
    (TUESDAY, "Tuesday"),
    (WEDNESDAY, "Wednesday"),
    (THURSDAY, "Thursday"),
    (FRIDAY, "Friday"),
    (SATURDAY, "Saturday"),
)

ANYTIME = 'anytime'
MORNING = "morning"
LUNCHTIME = "lunchtime"
AFTERNOON = "afternoon"
EVENING = "evening"
PREFFERED_TIME_CHOICES = (
    (ANYTIME, "Anytime"),
    (MORNING, "Morning, (8-11am)"),
    (LUNCHTIME, "Lunchtime (11am-1pm)"),
    (AFTERNOON, "Afternoon (1pm-5pm)"),
    (EVENING, "Evening (5pm-8pm)"),
)

FIRST_TIME_REASON = ('first time homebuyer', 'First time homebuyer')
SELLING_HOME_REASON = ('selling home moving', 'Selling home / moving')
SECOND_HOME_REASON = ('second home vacation home', 'Second home / vacation home')
INVESTMENT_PROPERTY_REASON = ('investment property', 'Investment property reason')
LOWER_MORTGAGE_PAYMENTS_REASON = ('lower mortgage payments', 'Lower mortgage payments')
LOWER_INTEREST_RATE_REASON = ('lower interest rate', 'Lower interest rate')
TAP_INTO_EQUITY_CASH_OUT_REASON = ('tap into equity cash out', 'Tap into equity / cash out')

PURCHASE_TYPE_CHOICES = (
    FIRST_TIME_REASON, SELLING_HOME_REASON, SECOND_HOME_REASON, INVESTMENT_PROPERTY_REASON
)

MORTGAGE_TIMINGS = (
    ('immediate', 'Immediate'),
    ('next_1_3_months', 'In the next 1-3 months'),
    ('just_researching', 'Just researching')
)

MORTGAGE_PROFILE_KINDS = (
    ('purchase', 'Purchase'),
    ('refinance', 'Refinance')
)


class EncompassMixin(object):
    """
    Provide custom formatting for Encompass Sync data.

    """
    def get_encompass_kind_display(self):
        return "Web - {}".format(self.get_kind_display())

    def get_encompass_created_display(self):
        return self.created.strftime("%B %d, %Y %H:%M")


class NotificationReceiverSet(QuerySet):
    def active(self):
        return self.filter(is_active=True)


class NotificationReceiver(TimeStampedModel):
    email = models.EmailField()
    encompass_user_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    # objects = PassThroughManager.for_queryset_class(NotificationReceiverSet)()
    objects = models.Manager.from_queryset(NotificationReceiverSet)()

    class Meta:
        ordering = ('created',)

    def __unicode__(self):
        return self.email


class ContactRequest(EncompassMixin, TimeStampedModel):
    """
    Parent model for different contact request kinds.

    Each child should contain ``CONTACT_REQUEST_KIND``.

    """
    KINDS = Choices(
        ('rate_quote_lead', 'rate_quote_lead', 'Rate Quote Submission'),
        ('consultation_request_lead', 'consultation_request_lead', 'Consultation Lead'),
        ('about_us_request', 'about_us_request', 'About Us Lead'),
        ('partner_lead', 'partner_lead', 'Partner Lead'),
        ('landing', 'landing', 'Landing Lead'),
        ('landing_page_extended_lead', 'landing_page_extended_lead', 'Landing Lead (Extended)'),
        ('mobile_profile_lead', 'mobile_profile_lead', 'Mobile Profile'),
        ('unlicensed_state', 'unlicensed_state', 'Unlicensed State'),
    )

    kind = models.CharField(max_length=255, choices=KINDS)
    user = models.ForeignKey(Customer, blank=True, null=True)
    advisor = models.ForeignKey(NotificationReceiver, blank=True, null=True)
    advisor_email = models.EmailField(blank=True, null=True)

    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    is_answered = models.BooleanField(default=False)
    contact_date = models.DateTimeField(null=True, blank=True)
    disposition = models.CharField(max_length=255, blank=True)

    # Encompass fields
    session_id = models.CharField(max_length=255, blank=True)
    last_sync = models.DateTimeField(blank=True, null=True)
    encompass_id = models.CharField(max_length=255, blank=True)
    crm_id = models.CharField(max_length=255, blank=True)
    crm_type = models.CharField(max_length=255, blank=True)
    uuid = UUIDField()
    utm_info = models.TextField(blank=True)

    objects = InheritanceManager()

    class Meta:
        ordering = ("is_answered", "-created")
        verbose_name = "Contact request"
        verbose_name_plural = "All contact requests"

    def __unicode__(self):
        return u"{} contact request. {} {}.".format(self.get_kind_display(), self.first_name, self.last_name)

    @property
    def _is_answered_updated(self):
        return (
            self.is_answered and not self.contact_date
        )

    def save(self, *args, **kwargs):
        self.kind = self.CONTACT_REQUEST_KIND

        if self._is_answered_updated:
            self.contact_date = now()

        return super(ContactRequest, self).save(*args, **kwargs)

    def get_admin_link(self):
        raise NotImplementedError


class ContactRequestMortgageProfile(ContactRequest):
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.rate_quote_lead

    email = models.EmailField()
    phone = models.CharField(max_length=255, blank=True)
    mortgage_profile = models.ForeignKey('mortgage_profiles.MortgageProfile', blank=True, null=True)

    class Meta(ContactRequest.Meta):
        verbose_name = "Rate Quote Submission"
        verbose_name_plural = "Rate Quote Submissions"

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_contactrequestmortgageprofile_change", (self.id,)


class ConsultationRequest(ContactRequest):
    """
    Stores consultation requests from home page
    """
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.consultation_request_lead

    mortgage_profile_kind = models.CharField(max_length=255, blank=True, choices=MORTGAGE_PROFILE_KINDS)

    purchase_type = models.CharField(max_length=255, blank=True, choices=PURCHASE_TYPE_CHOICES)
    mortgage_timing = models.CharField(max_length=255, choices=MORTGAGE_TIMINGS)
    phone = models.CharField(max_length=255)
    email = models.EmailField()
    preferred_time = models.CharField(max_length=255, default=MORNING,
                                      choices=PREFFERED_TIME_CHOICES)

    class Meta(ContactRequest.Meta):
        verbose_name = "Consultation Lead"
        verbose_name_plural = "Consultation Leads"

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_consultationrequest_change", (self.id,)


class ContactRequestAboutUs(ContactRequest):
    """
    Stores requests from page "About us"
    """
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.about_us_request

    email = models.EmailField()
    phone = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)

    class Meta(ContactRequest.Meta):
        verbose_name = "About Us Lead"
        verbose_name_plural = "About Us Leads"

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_contactrequestaboutus_change", (self.id,)


class ContactRequestPartner(ContactRequest):
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.partner_lead

    email = models.EmailField()

    class Meta(ContactRequest.Meta):
        verbose_name = 'Partners Lead'
        verbose_name_plural = 'Partners Leads'

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_contactrequestpartner_change", (self.id,)


class ContactRequestLanding(ContactRequest):
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.landing

    mortgage_profile_kind = models.CharField(max_length=255, blank=True, choices=MORTGAGE_PROFILE_KINDS)

    purchase_type = models.CharField(max_length=255, blank=True, choices=PURCHASE_TYPE_CHOICES)
    mortgage_timing = models.CharField(max_length=255, choices=MORTGAGE_TIMINGS)
    phone = models.CharField(max_length=255)
    email = models.EmailField()
    preferred_time = models.CharField(max_length=255, default=MORNING, choices=PREFFERED_TIME_CHOICES)

    class Meta(ContactRequest.Meta):
        verbose_name = "External Lead"
        verbose_name_plural = "External Leads"

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_contactrequestlanding_change", (self.id,)


class ContactRequestLandingExtended(ContactRequest):
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.landing_page_extended_lead

    phone = models.CharField(max_length=255)
    email = models.EmailField()

    mortgage_profile_kind = models.CharField(max_length=255, blank=True, choices=MORTGAGE_PROFILE_KINDS)
    property_zipcode = models.CharField(max_length=255, blank=True)
    property_state = models.CharField(max_length=255, blank=True)
    property_county = models.CharField(max_length=255, blank=True)
    is_veteran = models.NullBooleanField()
    credit_rating = models.CharField(max_length=255, blank=True)
    ownership_time = models.CharField(max_length=255, blank=True)

    annual_income_amount = models.PositiveIntegerField(blank=True, null=True)
    monthly_debt = models.PositiveIntegerField(blank=True, null=True)

    purchase_timing = models.CharField(max_length=255, blank=True)
    purchase_type = models.CharField(max_length=255, blank=True)
    purchase_property_value = models.PositiveIntegerField(blank=True, null=True)
    purchase_down_payment = models.PositiveIntegerField(blank=True, null=True)

    refinance_purpose = models.CharField(max_length=255, blank=True)
    refinance_cashout_amount = models.PositiveIntegerField(blank=True, null=True)
    refinance_property_value = models.PositiveIntegerField(blank=True, null=True)
    refinance_mortgage_balance = models.PositiveIntegerField(blank=True, null=True)

    class Meta(ContactRequest.Meta):
        verbose_name = "Landing Lead (Extended)"
        verbose_name_plural = "Landing Leads (Extended)"

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_contactrequestlandingextended_change", (self.id,)


class ContactRequestMobileProfile(ContactRequest):
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.mobile_profile_lead

    credit_rating = models.CharField(max_length=255, blank=True)
    annual_income_amount = models.PositiveIntegerField(blank=True, null=True)
    monthly_housing_expense = models.PositiveIntegerField(blank=True, null=True)
    monthly_nonhousing_expense = models.PositiveIntegerField(blank=True, null=True)
    down_payment_amount = models.PositiveIntegerField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    mortgage_profile = models.ForeignKey('mortgage_profiles.MortgageProfile', blank=True, null=True)
    steps_progress = JSONField(blank=True, null=True)

    class Meta(ContactRequest.Meta):
        verbose_name = "Mobile Profile"
        verbose_name_plural = "Mobile Profiles"

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_contactrequestmobileprofile_change", (self.id,)


class ContactRequestUnlicensedState(ContactRequest):
    STATE_CODES = [(state_code, state_code) for state_code in settings.STATE_CODES]
    CONTACT_REQUEST_KIND = ContactRequest.KINDS.unlicensed_state

    email = models.EmailField(blank=False, null=False)
    phone = models.CharField(max_length=255, blank=True, null=True)
    unlicensed_state_code = models.CharField(max_length=255, blank=False, null=True, choices=STATE_CODES)

    class Meta(ContactRequest.Meta):
        verbose_name = "Unlicensed State Contact Request"
        verbose_name_plural = "Unlicensed State Contact Requests"

    @models.permalink
    def get_admin_link(self):
        return "admin:contacts_contactrequestunlicensedstate_change", (self.id,)


class Location(models.Model):
    zipcode = models.CharField(max_length=10, db_index=True)
    state = models.CharField(max_length=255, db_index=True)
    county = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

    def __unicode__(self):
        return '{0}, {1}, {2}, {3}'.format(
            self.zipcode, self.state, self.county, self.city
        )
