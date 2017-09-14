from django.conf import settings

from rest_framework.permissions import BasePermission


class BoxEventCallbackPermission(BasePermission):
    """
    Check that request was created by box service.
    """
    def has_permission(self, request, view):
        return request.GET.get('token') == settings.BOX_API_OAUTH_CLIENT_ID
