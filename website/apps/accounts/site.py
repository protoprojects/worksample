from django.contrib.admin.sites import AdminSite
from django.http import HttpResponseRedirect
from django.conf import settings

from accounts import duo_auth


class DuoAdminSite(AdminSite):
    def login(self, request, extra_context=None):
        """
        Splits login flow into two sub flows:
        - django login
        - duo login if django login was passed

        """

        if not request.user.is_authenticated():
            response = super(DuoAdminSite, self).login(request, extra_context)
            if isinstance(response, HttpResponseRedirect):
                return duo_auth.login(request)
            else:
                return response
        else:
            return duo_auth.login(request)

    def logout(self, request, extra_context=None):
        duo_auth.duo_unauthenticate(request)
        return super(DuoAdminSite, self).logout(request, extra_context)

    def has_permission(self, request):
        return super(DuoAdminSite, self).has_permission(request) and duo_auth.duo_authenticated(request)
