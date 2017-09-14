import functools
import inspect
import logging
import hashlib
import json
import re

import shortuuid
from uuid import UUID

from celery import Task

from django.db import connection
from django.conf import settings
from django.core.cache import caches

from pinax.notifications import models as notification

from string import lower

from accounts.models import User
from core.exceptions import ServiceUnavailableException

from moneyed import Money, USD
from moneyed.localization import format_money

logger = logging.getLogger('sample.core.utils')


def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer


def get_state_code(state_name):
    """
    Returns state code by state_name ex: get_state_code('California') => CA
    """
    if state_name is None:
        return None
    if state_name.upper() in settings.STATE_CODES:
        # if the value passed in is actually a "code" return that value
        return state_name.upper()
    return settings.STATES_MAP.get(state_name.title())


def get_state_name(state_code):
    """
    Returns state code by state_name ex: get_state_code('California') => CA
    """
    if state_code is None:
        return None
    if state_code.title() in settings.STATE_NAMES:
        # if the value passed in is actually a "name" return that value
        return state_code.title()
    state_codes_map = {value: key for key, value in settings.STATES_MAP.items()}
    return state_codes_map.get(state_code.upper())


def is_sample_email(email):
    return email.endswith('@sample.com')


class LogMuter(object):
    """Mute specified loggers by increasing log level"""
    def __init__(self, log_names, mute_level=logging.WARN):
        self.loggers = {}
        self.mute_level = mute_level
        for name in log_names:
            logger = logging.getLogger(name)
            self.loggers[logger] = logger.level

    def mute(self):
        """Set loggers to the mute level"""
        for logger in self.loggers:
            logger.setLevel(self.mute_level)

    def restore(self):
        """Restore loggers to their previous level"""
        for logger, level in self.loggers.items():
            logger.setLevel(level)


class LogMutingTestMixinBase(object):
    """Base mixin for muting log output during unit tests

    Usage
      - the log_names class variable specifies which logs are muted
      - the mute_level class variable sets the temporary log level

    """
    log_names = []
    mute_level = logging.WARN

    def setUp(self):
        super(LogMutingTestMixinBase, self).setUp()
        self.log_muter = LogMuter(self.log_names, self.mute_level)
        self.log_muter.mute()

    def tearDown(self):
        self.log_muter.restore()
        super(LogMutingTestMixinBase, self).tearDown()


class FullDiffMixin(object):
    '''Avoid truncating diff output from assert failures'''
    maxDiff = None


def is_uuid4(uuid_str):
    '''checks that the uuid is a valid uuid4'''
    uuid_str = str(uuid_str)
    try:
        UUID(uuid_str, version=4)
        return True
    except ValueError:
        # If it's a value error, then the string
        # is not a valid hex code for a UUID.
        return False


def clear_session(request):
    """
    clears the entire session
    in particular want to ensure that, in many cases, the
    mortgage_profile_uuid is deleted so that the user cannot make changes
    to the mortgage profile after their application is completed
    """
    session = getattr(request, 'session', False)
    if session:
        session.flush()


def create_shortuuid():
    return shortuuid.uuid()


def send_exception_notification(lp_guid, exception_source, exception_msg):
    """
    :param exception_source: Twilio, Box, Encompass, etc.
    :param exception_msg: Exception details msg.
    """
    ctx = {
        'stage': settings.STAGE,
        'lp_guid': lp_guid,
        'exception_source': exception_source,
        'exception_msg': exception_msg,
    }
    # recipient should be User instance
    user = User(email=settings.EXCEPTION_NOTIFICATION_EMAIL, id=1)
    notification.send([user], 'exception_notification', ctx)


def format_logger_args(func, args, kwargs, custom_log=None):
    """
    Used for generating string by format string syntax

    :param func: function object
    :param args: function args
    :param kwargs: function kwargs dict
    :type kwargs: dict
    :param custom_log: format string syntax
    :type custom_log: str
    :return: formatted string by format string syntax
    :rtype: str
    """
    call_kwargs = inspect.getcallargs(func, *args, **kwargs)
    if custom_log:
        return custom_log.format(**call_kwargs)
    return ' '.join(['{} {}'.format(key, arg) for key, arg in call_kwargs.items()])


def service_unavailable_notification(service_name, custom_log=None):
    """
    Decorator for functions that rises ServiceUnavailableException.
    Sends email notification about what service is unavailable and which loan profile was processed.

    Raises:
        ServiceUnavailableException
    Example usage:
        @service_unavailable_notification(service_name='Box', custom_log='{loan_profile.guid}')
        def get_or_create_loan_profile_box_folder(loan_profile, external_template):
            ...
        If get_or_create_loan_profile_box_folder function rises ServiceUnavailableException, function send_exception_notification
        will be called with arguments lp_guid = loan_profile.guid, service_name = 'Box'

    :param service_name: Box, Twilio, Salesforce etc.
    :type service_name: str
    :param custom_log: format string syntax
    :type custom_log: str
    """
    def wrapper(func):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ServiceUnavailableException as exc:
                lp_guid = format_logger_args(func, args, kwargs, custom_log)
                send_exception_notification(lp_guid, service_name, str(exc))
                raise
        return inner
    return wrapper


class SynchronousTask(Task):
    """
    Block running parallel tasks. In one time running one task for unique lock key.

    prefix_lock_key: Set if need custom prefix for look key
    retry_on_lock: If True run retry if task locked
    retry_countdown_lock: Countdown for retry task
    time_expiration_lock: Timeout for lock key
    use_args_in_lock_name bool: If True used args for generate suffix lock key
    cache_name: Name for django cache system
    """

    prefix_lock_key = None
    retry_on_lock = False
    time_expiration_lock = settings.CELERY_TIME_EXPIRATION_LOCK
    retry_countdown_lock = 5
    use_args_in_lock_key = True
    cache_name = 'celery'

    def get_cache(self):
        return caches[self.cache_name]

    def get_prefix_lock_key(self):
        return self.prefix_lock_key or '%s.%s' % (self.__module__, self.__name__)

    def get_suffix_lock_key(self, *args, **kwargs):
        if self.use_args_in_lock_key:
            _hash = hashlib.sha1(json.dumps(args))
            _hash.update(json.dumps(kwargs))
            return _hash.hexdigest()
        return ''

    def get_lock_key(self, args, kwargs):
        prefix_lock_key = self.get_prefix_lock_key()
        suffix_lock_key = self.get_suffix_lock_key(*args, **kwargs)
        return '%s.%s' % (prefix_lock_key, suffix_lock_key)

    def run(self, *args, **kwargs):
        lock_key = self.get_lock_key(args, kwargs)
        cache_key = self.get_cache()

        # Add a value to the cache, failing if the key already exists.
        # Returns True if the object was added, False if not.
        is_locked = cache_key.add(lock_key, 'True', self.time_expiration_lock)
        if is_locked:
            try:
                return self.synchronous_run(*args, **kwargs)
            finally:
                cache_key.delete(lock_key)
        if self.retry_on_lock:
            raise self.retry(countdown=self.retry_countdown_lock)

    def synchronous_run(self, *args, **kwargs):
        raise NotImplementedError


def get_consumer_portal_base_url():
    return '{}://{}'.format(settings.CP_URL['PROTOCOL'], settings.CP_URL['HOST'])


def mask_phone_number(phone_number):
    """
    Used for PII phone number protection

    :param phone_number: string to obfuscate
    :type phone_number: str
    :return: last 4 string characters of phone_number param
    :rtype: str
    """
    return phone_number[-4:]


def mask_email(email, offset=1):
    """
    Used for PII email protection.

    Example:
        mask_email('nickname@gmail.com')
        returns 'n******@gmail.com'

    :param email: email string
    :type email: str
    :param offset: Number of characters to be replaced from the beginning of the 'local_part' email string
    :type offset: int
    :return: obfuscated email
    :rtype: str
    """
    mask_char = '*'
    local_part, domain = email.split('@')
    masked_local_part = '{}{}'.format(local_part[:offset], mask_char * len(local_part[offset:]))
    return '{}@{}'.format(masked_local_part, domain)


def mask_digits(string, mask_char='#'):
    """
    Used for PII protection.
    Replace all digits to '#' character.

    :param string: string to obfuscate
    :type string: str
    :param mask_char: string to obfuscate
    :type mask_char: character for digit replacing
    :return: obfuscated string
    :rtype: str
    """
    return re.sub('\d', mask_char, string)


def mask_currency_value(string, mask_string='#,###.##'):
    """
    Used for PII protection.
    Replace currency value in string with mask_string param.

    :param string: string to obfuscate
    :type string: str
    :param mask_string: value for replacing
    :type mask_string: str
    :return: obfuscated string
    :rtype: str
    """
    return re.sub('\d+(\.\d{1,2})?', mask_string, string)


def db_connection_close(func=None):
    """
    Close database connection after running function

    Notes:
        Needing for concurrency tests running in threads
    """
    def wrapper(func):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            finally:
                connection.close()
        return inner
    if func:
        return wrapper(func)
    return wrapper


class SubstringMatcher(object):
    def __init__(self, containing):
        self.containing = lower(containing)

    def __eq__(self, other):
        return lower(other).find(self.containing) > -1

    def __unicode__(self):
        return 'a string containing "%s"' % self.containing

    def __str__(self):
        return unicode(self).encode('utf-8')

    __repr__ = __unicode__

def as_currency(dollar_amount):
    return format_money(Money(dollar_amount, USD), locale='en_US', decimal_places=0)
