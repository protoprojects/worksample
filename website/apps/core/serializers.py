# -*- coding: utf-8 -*-
from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework_jwt.settings import api_settings


jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
jwt_decode_handler = api_settings.JWT_DECODE_HANDLER


# pylint: disable=W0223
class JSONWebTokenSerializer(serializers.Serializer):
    """
    Basic serializer class used to validate a username and password.

    `USER_GROUP_VALIDATOR` must be implemented in inheritors to perform
    specific validation, based on the group of user instance.
    Payload will be returned, if validator returns `TRUE`.

    Returns a JSON Web Token that can be used to authenticate later calls.
    """
    USER_GROUP_VALIDATOR_FUNC = None

    MESSAGES = {
        'invalid_credentials': 'Unable to login with provided credentials.',
        'incorrect_data': '"Username" and "password" must be specified.',
        'user_is_disabled': 'User account is disabled.',
    }

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    @property
    def object(self):
        return self.validated_data

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                if not user.is_active:
                    raise serializers.ValidationError(self.MESSAGES['user_is_disabled'])

                if not self.USER_GROUP_VALIDATOR_FUNC:
                    raise NotImplementedError('Validator must be implemented.')

                # pylint: disable=not-callable
                if self.USER_GROUP_VALIDATOR_FUNC(user):
                    payload = jwt_payload_handler(user)

                    return {
                        'token': jwt_encode_handler(payload)
                    }
                else:
                    raise serializers.ValidationError(self.MESSAGES['invalid_credentials'])
            else:
                raise serializers.ValidationError(self.MESSAGES['invalid_credentials'])
        else:
            raise serializers.ValidationError(self.MESSAGES['incorrect_data'])


# pylint: disable=W0223
class VerifyJSONWebTokenSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        try:
            jwt_decode_handler(attrs.get('token'))
        except Exception:
            raise serializers.ValidationError('Wrong or expired token')
        else:
            return {}
