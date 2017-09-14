import logging

from twilio.rest import TwilioRestClient
from twilio.rest.exceptions import TwilioException

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from core.exceptions import ServiceUnavailableException

logger = logging.getLogger('core.twilio')


class TwilioServiceUnavailableException(ServiceUnavailableException):
    default_detail = _('Twilio service temporarily unavailable.')


def create_sms(phone_number, message):
    """
    Send sms via Twilio.

    :param phone_number: Recipient phone number in the form of +14152003850
    :param message: Message body to send to the recipient

    :raises TwilioException: if the message fails to send.
    """
    logger.debug('TWILIO-SEND-SMS to phone number ends with %s', phone_number[-4:])

    client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        response = client.messages.create(
            to=phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            body=message)
        logger.debug('TWILIO-SEND-SMS sent "%s" to phone nymber ending with %s. SMS sid %s',
                     message, phone_number[-4:], response.sid)
    except TwilioException:
        logger.exception('TWILIO-SEND-SMS-FAIL to phone number ending with %s', phone_number[-4:])
        raise


def create_call(phone_number, callback_url):
    """
    Create call via Twilio.

    :param phone_number: Recipient phone number in the form of +14152003850
    :param callback_url:
        For confirmation by call, we can't send voice message, but can send callback url,
        where TwiML will respond.
        https://www.twilio.com/docs/api/twiml

    :raises TwilioException: if the call fails.
    """
    logger.debug('TWILIO-CREATE-CALL phone number ends with %s, callback url %s',
                 phone_number[-4:], callback_url)

    client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        client.calls.create(to=phone_number, from_=settings.TWILIO_PHONE_NUMBER, url=callback_url)
    except TwilioException:
        logger.exception('TWILIO-CREATE-CALL-FAIL Callback URL: %s', callback_url)
        raise
