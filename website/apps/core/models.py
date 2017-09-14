# -*- coding: utf-8 -*-
import logging
import uuid
from datetime import datetime, timedelta
from itertools import izip_longest
from pytz import UTC

from django.db import models

from encrypted_fields import EncryptedFieldMixin
from solo.models import SingletonModel

logger = logging.getLogger('sample.core.models')

MORTGAGE_TYPE_CHOICES = (
    ('fixed', 'Fixed'),
    ('adjustable', 'Adjustable'),
    ('interest_only', 'Interest Only'),
)


##############################
# Singletons                 #
##############################
class OfficeAddress(SingletonModel):
    address = models.CharField(max_length=100)
    suite = models.CharField(max_length=30)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=20)
    zipcode = models.CharField(max_length=20)
    house_number = models.CharField(max_length=20)
    longitude = models.FloatField(default=0)
    latitude = models.FloatField(default=0)


class EncompassSync(SingletonModel):
    enable = models.BooleanField(default=True)

    @classmethod
    def enabled(cls):
        return cls.get_solo().enable

    class Meta:
        verbose_name = "Encompass Sync"


class Recaptcha(SingletonModel):
    enable = models.BooleanField(default=True)
    site_key = models.CharField(max_length=100)
    secret_key = models.CharField(max_length=100)
    verification_url = models.CharField(max_length=100, default='https://www.google.com/recaptcha/api/siteverify')

    @classmethod
    def enabled(cls):
        return cls.get_solo().enable


##############################
# Other                      #
##############################
class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.

    """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ResetTokenManager(models.Manager):
    def fetch(self, customer):
        """
        gets or creates the token to be used in the email sent to the customer.

        note: did not use the standard get_or_create, since .updated needed to be set
        """
        now = datetime.utcnow().replace(tzinfo=UTC)
        reset_token = self.filter(customer=customer).first()
        if reset_token:
            reset_token.updated = now
            reset_token.save()
            return reset_token
        else:
            return super(ResetTokenManager, self).create(customer=customer, updated=now)

    def get_valid_token(self, token):
        """
        gets a valid reset_token based for a given token (uuid).
        Used to validate the reset_token sent to the server to reset the password.
        """
        reset_token = self.filter(token=token).first()
        if reset_token and reset_token.has_expired:
            reset_token.delete()
            return None
        return reset_token

    def create(self, *args, **kwargs):
        raise NotImplementedError('use .fetch instead of .create')

    def update_or_create(self, *args, **kwargs):
        raise NotImplementedError('use .fetch instead of .update_or_create')

    def get_or_create(self, *args, **kwargs):
        raise NotImplementedError('use .fetch instead of .get_or_create')

    def get(self, *args, **kwargs):
        raise NotImplementedError('use .get_valid_token instead')


class ResetToken(TimeStampedModel):
    """
    a onetime use token for resetting passwords.
      * There should be only one token outstanding per customer
      * A token, if one exists, should be deleted on successful login
        using customer.delete_reset_token_if_exists()
      * if a reset_token is requested, while one still exists,
        the existing token's .updated timestamp is refreshed,
        which is why .expiration relies on .updated not .created

    for an example of the implementation see the customer_portal
    """
    EXPIRATION_IN_HOURS = 24

    customer = models.OneToOneField(
        'accounts.Customer',
        on_delete=models.SET_NULL,
        related_name='reset_token',
        null=True,
        blank=True
    )
    token = models.UUIDField(
        primary_key=False,
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    objects = ResetTokenManager()

    @property
    def expiration(self):
        return self.updated + timedelta(hours=self.EXPIRATION_IN_HOURS)

    @property
    def has_expired(self):
        return self.expiration < datetime.utcnow().replace(tzinfo=UTC)


class PortionMixin(object):
    """
    Manager mixing for devide objects to portions.

    """
    def by_portions(self, count):
        """
        Return list of objects devided to portions by `count`.

        """
        return [portion
                for portion in izip_longest(*[iter(self.get_queryset())] * count, fillvalue=None)
                if portion]


class EncryptedNullBooleanField(EncryptedFieldMixin, models.NullBooleanField):
    pass


class EncryptedPositiveIntegerField(EncryptedFieldMixin, models.PositiveIntegerField):
    pass


class EncryptedDataField(EncryptedFieldMixin, models.DateField):
    pass
