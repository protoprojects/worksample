import logging
import copy
import requests
from requests.exceptions import RequestException

from rest_framework import serializers

from core import models as core_models
from ipware.ip import get_real_ip

logger = logging.getLogger(__name__)


class RecaptchaValidator(object):
    def __init__(self):
        self.request = None

    def __call__(self, value):
        recaptcha_settings = core_models.Recaptcha.get_solo()
        if not recaptcha_settings.enable:
            logger.warning('RECAPTCHA-NOT-ENABLED')
            return

        request_data = {
            'secret': recaptcha_settings.secret_key,
            'response': value,
        }

        if self.request:
            remote_ip = get_real_ip(self.request)
            if remote_ip:
                request_data['remoteip'] = remote_ip
            else:
                logger.warning('RECAPTCHA-REMOTE-IP not found real ip in request')

        try:
            response = requests.post(recaptcha_settings.verification_url, data=request_data)
        except RequestException:
            logger.exception('RECAPTCHA-VERIFIED request %s', request_data)
            raise serializers.ValidationError('Request failed')

        # expected response:
        # {
        #   "success": true|false,
        #   "challenge_ts": timestamp,  // timestamp of the challenge load (ISO format yyyy-MM-dd'T'HH:mm:ssZZ)
        #   "hostname": string,         // the hostname of the site where the reCAPTCHA was solved
        #   "error-codes": [...]        // optional
        # }

        logger_request_data = copy.deepcopy(request_data)
        logger_request_data['secret'] = 'XXXXXXXXXXXXXXXXXX{0}'.format(
            recaptcha_settings.secret_key[-3:])
        logger.info('RECAPTCHA-RESPONSE request %s response %s',
                    logger_request_data, response.content)

        try:
            response_data = response.json()
        except ValueError:
            logger.exception('RECAPTCHA-FAILED')
            raise serializers.ValidationError('Response failed')

        success = response_data.get('success')
        if success:
            logger.info('RECAPTCHA-VERIFIED')
        else:
            logger.info('RECAPTCHA-FAILED')
            raise serializers.ValidationError('Validation failed')

    def set_context(self, serializer_field):
        if 'request' in serializer_field.context:
            self.request = serializer_field.context['request']


class RecaptchaMixin(serializers.Serializer):
    recaptcha_response = serializers.CharField(validators=[RecaptchaValidator()], write_only=True)

    def __init__(self, *args, **kwargs):
        super(RecaptchaMixin, self).__init__(*args, **kwargs)
        settings = core_models.Recaptcha.get_solo()
        if not settings.enable and 'recaptcha_response' in self.fields:
            self.fields.pop('recaptcha_response')

    @property
    def validated_data(self):
        data = super(RecaptchaMixin, self).validated_data
        if 'recaptcha_response' in data:
            del data['recaptcha_response']
        return data
