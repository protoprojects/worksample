from django.conf import settings

from rest_framework.permissions import BasePermission


class DenyAllPermission(BasePermission):
    """
    Just a class-reminder to be overriden in inheritors.
    """

    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


class TwilioCallbackPermission(BasePermission):
    """
    Check that request was created by twilio service.
    """
    def has_permission(self, request, view):
        return request.POST.get('AccountSid') == settings.TWILIO_ACCOUNT_SID
