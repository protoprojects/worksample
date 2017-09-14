# -*- coding: utf-8 -*-
import logging
import random
import string
import uuid

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.http import urlencode
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin

from django.contrib.postgres.fields import JSONField
from shortuuidfield import ShortUUIDField
from sorl.thumbnail import ImageField
from model_utils import Choices
from model_utils.managers import InheritanceManager
from rest_framework import serializers
from solo.models import SingletonModel

from accounts.validators import validate_contact_preferences
from core import twilio_utils
from core.models import TimeStampedModel

logger = logging.getLogger('sample.accounts.models')


class PhoneVerification(TimeStampedModel):
    """ Model used to verify phone numbers for direct registration """

    VERIFICATION_METHOD_CHOICES = Choices(
        ('sms', 'Sms'),
        ('call', 'Call')
    )

    phone = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ['phone', 'email']

    def save(self, *args, **kwargs):
        """
        Saves the phone verification message. If the verification code
        has not yet been created, this will generate a random code and
        save it.

        :returns: saved model
        """
        if not self.code:
            self.code = self.generate_verification_code()

        return TimeStampedModel.save(self, *args, **kwargs)

    def send_code(self, method):
        """
        Sends code via twilio service.

        :param method: choice from PhoneVerification.VERIFICATION_METHOD_CHOICES
        :type method: str
        :returns: None
        """
        if method == self.VERIFICATION_METHOD_CHOICES.call:
            callback_url = self._build_callback_url()
            twilio_utils.create_call(self.phone, callback_url)
        else:
            msg = 'Your verification code is {}'.format(self.code)
            twilio_utils.create_sms(self.phone, msg)

    def _build_callback_url(self):
        """
        :returns: callback url for twilio service callback. Optional parameter for phone call verification
                  since we can't leave a voicemail. See https://www.twilio.com/docs/api/twiml
        :rtype: str
        """
        url = settings.SITE_PATH + reverse('accounts:api-phone-verification-twilio-callback')
        url += '?' + urlencode({'verification_code': self.code})
        return url

    @staticmethod
    def generate_verification_code():
        """
        Generates a random 6 digit number for use in verification

        :returns: a string of 6 random digits
        """
        return ''.join((random.choice(string.digits) for i in range(6)))


class UserManager(BaseUserManager, InheritanceManager):
    """ User manager for the phone verification service """

    def create_user(self, email, password=None, **kwargs):
        """
        Creates a User

        :param email: email address of the User
        :param password: optional password
        :param **kwargs: additional keyword arguments

        :returns: a consumer user object
        """
        now = timezone.now()
        email = self.normalize_email(email)

        user = self.model(
            email=email,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            last_login=now,
            date_joined=now,
            **kwargs
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, **kwargs):
        """
        Create a superuser

        :param **kwargs: at the very least, this contains `email`,
            but will also contain other keys used in creating a
            super User

        :returns: a super user object
        """
        user = self.create_user(**kwargs)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

    def create_user_with_random_password(self, email, **kwargs):
        """
        Create a consumer user with a random password

        :param email: email address of the User
        :param **kwargs: additional keyword arguments
            If `password` is included, it will be overwritten

        :returns: a user object with a random password
        """
        password = self.make_random_password()
        return self.create_user(email, password, **kwargs), password


class CustomUserManager(UserManager):
    """ Class for Custom Users """

    def get_by_natural_key(self, username):
        """
        Use model-specific username field for lookup.

        :param username: username to look up

        :returns: instance of a user that matches the username
        """
        return self.get_subclass(**{self.model.USERNAME_FIELD: username})

    def generate_account_number(self, length=8):
        """
        Generate a random account number for a user.

        :param length: length (int) of the account number. Defaults to 8
        :returns: account number (str) of `length` digits
        """
        while True:
            account_number = ''.join((random.choice(string.digits) for i in range(length)))
            if not self.get_queryset().filter(account_number=account_number).exists():
                break
        return account_number

    def fetch_user_or_raise_error(self, email, data=None):
        """
        mimics the functionality of .get_or_create, but performs the additional check
        that the user being .get_or_create'd is of the correct User class
        """
        data = {} if data is None else data
        users = User.objects.select_subclasses().filter(email=email)
        if users.exists():
            user = users.first()
            if not isinstance(user, self.model):
                raise serializers.ValidationError(
                    {'errors': ['email already exists for a different type of user']})
            created = False
        else:
            user = self.model.objects.create(email=email, **data)
            created = True
        return (user, created)


class User(AbstractBaseUser, PermissionsMixin):
    """Base User model"""

    email = models.EmailField(max_length=255, unique=True)
    phone = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    avatar = ImageField(upload_to="avatars", blank=True, null=True)
    guid = models.UUIDField(
        primary_key=False,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )

    phone_verification = models.OneToOneField(PhoneVerification,
                                              on_delete=models.SET_NULL,
                                              null=True,
                                              blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    class Meta:
        ordering = ('email', 'last_name', 'first_name')

    def __unicode__(self):
        return u"{first_name} {last_name} <{email}>".format(
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
        )

    def get_full_name(self):
        return u"{0.first_name} {0.last_name}".format(self)

    def get_short_name(self):
        return self.first_name

    @property
    def username(self):
        """Convienience property method for admin interface"""
        return u"{0.first_name} {0.last_name}".format(self)

    def is_advisor(self):
        """Convenience check to determine if a user is an advisor"""
        return self.groups.filter(name='mortgage_advisors').exists()

    # pylint: disable=no-self-use
    def is_customer(self):
        """Convenience check to determine if a user is a customer. Not used."""
        return False

    # pylint: disable=no-self-use
    def is_realtor(self):
        """Convenience check to determine if a user is a realtor. Not used."""
        return False

    @property
    def is_phone_number_verified(self):
        """Convenience check to determine if the phone number is verified."""
        return getattr(self.phone_verification, 'is_verified', False)


class Advisor(User):
    """Mortgage advisor"""

    title = models.CharField(max_length=255, blank=True)
    short_biography = models.TextField(blank=True)
    about = models.ForeignKey('pages.AboutAdvisor', blank=True, null=True)
    nmls_number = models.CharField(max_length=255, blank=True, verbose_name="NMLS #")
    encompass_id = models.CharField(null=True, blank=True, max_length=64)
    profile_key = models.CharField(max_length=255, blank=True)

    def is_advisor(self):
        return True

    @property
    def profile_url(self):
        """Convenience check to return the profile URL."""
        if self.profile_key:
            return "{0}://{1}{2}{3}".format(
                settings.ADVISOR_PROFILE_URL['PROTOCOL'],
                settings.ADVISOR_PROFILE_URL['HOST'],
                settings.ADVISOR_PROFILE_URL['STEM'],
                self.profile_key)
        return None


class DefaultAdvisor(SingletonModel):
    """
    the default advisor used that is assigned to a loan if salesforce fails to return
    an advisor email
    """
    default_advisor = models.OneToOneField(
        Advisor,
        on_delete=models.SET_NULL,
        null=True,
        blank=False
    )


class Specialist(User):
    """Mortgage specialist"""

    title = models.CharField(max_length=255, blank=True)
    short_biography = models.TextField(blank=True)
    encompass_id = models.CharField(null=True, blank=True, max_length=64)


class Coordinator(User):
    """Mortgage coordinator"""

    title = models.CharField(max_length=255, blank=True)
    short_biography = models.TextField(blank=True)
    encompass_id = models.CharField(null=True, blank=True, max_length=64)


class CustomerEmailValidation(models.Model):
    """codes for Customer user email verification"""

    # ALIBI: want to keep this off of core user tables for R/RW split
    is_active = models.BooleanField(default=True)
    is_redeemed = models.BooleanField(default=False)
    code = ShortUUIDField()

    def __str__(self):
        return u"redeemed: {0.is_redeemed} active: {0.is_active} (code: {0.code})".format(self)

    def verify(self):
        """Method to set a user's email to verified"""
        self.is_redeemed = True
        self.save()

    def decline(self):
        """Method to decline verification of a user's email"""
        self.is_redeemed = False
        self.is_active = False
        self.save()


class Customer(User):
    """Customer aka potential borrower"""

    COMMUNICATION_PREFERENCES = Choices(('phone', 'Phone'), ('email', 'Email'))
    SOURCES = Choices('rate_quote', 'advisor_portal_link')

    PHONE_KINDS = Choices(('office', 'Office'), ('home', 'Home'), ('mobile', 'Mobile'))

    # choices are from https://www.w3.org/International/articles/language-tags/
    LANGUAGES = Choices(
        ('cmn', 'mandarin', 'Mandarin'),
        ('en', 'english', 'English'),
        ('es', 'spanish', 'Spanish'),
        ('yue', 'cantonese', 'Cantonese'),
    )

    DEFAULT_CONTACT_PREFERENCES = {
        'phone_ok': True,
        'email_ok': True,
        'text_ok': False,
    }

    advisor = models.ForeignKey(Advisor, blank=True, null=True)
    realtor = models.ForeignKey('Realtor', related_name='customers', blank=True, null=True)

    # contact_preferences are preferences for communicating during the loan process
    contact_preferences = JSONField(default=DEFAULT_CONTACT_PREFERENCES,
                                    validators=[validate_contact_preferences])
    has_opted_out_of_email = models.NullBooleanField(default=False)
    phone_kind = models.CharField(max_length=255, blank=True, null=True, choices=PHONE_KINDS)
    preferred_language = models.CharField(default=LANGUAGES.english, max_length=255, blank=True,
                                          null=True, choices=LANGUAGES)

    # to be removed
    preference_communication = models.CharField(blank=True, max_length=255,
                                                choices=COMMUNICATION_PREFERENCES)
    account_number = models.CharField(max_length=255, unique=True)
    transactional_emails_subscribed = models.BooleanField(default=True)
    lifecycle_emails_subscribed = models.BooleanField(default=True)
    marketing_emails_subscribed = models.BooleanField(default=True)
    surveys_reminders_subscribed = models.BooleanField(default=True)

    # transaction details
    # to be removed
    purchase_timing = models.CharField(max_length=255, blank=True)
    financing_contingency_date = models.DateField(blank=True, null=True)
    down_payment_value = models.IntegerField(blank=True, null=True)
    credit_rating = models.CharField(max_length=255, blank=True)
    income = models.IntegerField(null=True, blank=True)
    inspector = models.CharField(max_length=255, blank=True)
    appraisal_company = models.CharField(max_length=512, blank=True)
    title_company = models.CharField(max_length=512, blank=True)

    email_validation = models.OneToOneField(
        CustomerEmailValidation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = Customer.objects.generate_account_number()

        return super(Customer, self).save(*args, **kwargs)

    def has_reset_token(self):
        """Convenience method to determine if a reset token exists for the customer"""
        return hasattr(self, 'reset_token')

    def delete_reset_token_if_exists(self):
        """Convenience method to delete a reset token if it exists"""
        return self.has_reset_token() and self.reset_token.delete()

    def is_customer(self):
        return True

    @property
    def source(self):
        """Convenience method to determine the customer source"""
        mps = self.mortgage_profiles.all()
        return (self.SOURCES.rate_quote if self.mortgage_profiles.exists()
                else self.SOURCES.advisor_portal_link)

    @property
    def is_email_verified(self):
        """Convenience method to determine if the email has been verified"""
        if self.email_validation:
            if self.email_validation.is_redeemed and self.email_validation.is_active:
                return True
        return False

    @property
    def current_loan_profile(self):
        """Convenience method to determine if this is the customers current loan profile"""
        return self.loan_profilesv1.filter(is_active=True).order_by('-created').first()

    def check_for_duplicate_email(self, log_info=False):
        """
        Checks to see if the email address entered has already been used

        :param log_info: determines whether a log message should be included. Default is False.
        """
        if self.email:
            customers = Customer.objects.filter(email__iexact=self.email)
            has_duplicates = customers.count() > 1
            if has_duplicates and log_info:
                logger.info('CP-DUPLICATE-EMAIL-USERNAME-EXISTS customer_ids %s',
                            customers.values_list('id'))
            return has_duplicates
        else:
            # should never happen, since email is required
            return None


class CustomerProtectedProxyModel(Customer):
    """Used for PII protection."""

    class Meta:
        proxy = True
        verbose_name = 'Customer'

    def __unicode__(self):
        if settings.STAGE == 'prod':
            from core.utils import mask_email

            return u"{first_name} {last_name} <{email}>".format(
                first_name=self.first_name,
                last_name=self.last_name,
                email=mask_email(self.email),
            )
        return super(CustomerProtectedProxyModel, self).__unicode__()


class Realtor(User):
    """Real estate agent"""

    objects = CustomUserManager()

    def is_realtor(self):
        return True


class Address(models.Model):
    """Customer address"""

    kind = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    zipcode = models.CharField(max_length=255)
    customer = models.ForeignKey('Customer', related_name='addresses')

    def __unicode__(self):
        return u'{0.state} {0.city} {0.zipcode}'.format(self)
