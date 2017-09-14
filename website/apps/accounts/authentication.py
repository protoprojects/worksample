from rest_framework import exceptions
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from accounts.models import User


class CustomWebTokenAuthentication(JSONWebTokenAuthentication):
    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        try:
            user_id = payload.get('user_id')

            if user_id:
                user = User.objects.get_subclass(pk=user_id, is_active=True)
            else:
                msg = 'Invalid payload'
                raise exceptions.AuthenticationFailed(msg)
        except User.DoesNotExist:
            msg = 'Invalid signature. User does not exist'
            raise exceptions.AuthenticationFailed(msg)

        return user
