import re

from django.conf import settings

from rest_framework.permissions import BasePermission

from loans.models import LoanProfileV1


class AllowAdvisorPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_advisor()

    def has_object_permission(self, request, view, obj):
        return request.user.is_advisor()


class ModifyOperationsPermission(BasePermission):
    """
    If loan profile was submitted to encompass,
    need to perform a check to prevent edition
    of submitted one.
    """

    RESTRICTED_METHODS = ["POST", "PATCH", "PUT", "DELETE"]

    # pylint: disable=no-self-use
    @property
    def limitation_enabled(self):
        return getattr(settings, 'ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED', False)

    def _perform_check(self, request, loan_profile_obj):
        if not self.limitation_enabled:
            return True
        if (request.method in self.RESTRICTED_METHODS and
                loan_profile_obj.encompass_sync_status == LoanProfileV1.ENCOMPASS_SYNCED):
            return False
        return True

    def has_permission(self, request, view):
        try:
            # FIXME: need to find a way to avoid hardcoding url
            # pylint: disable=protected-access
            loan_profile_id = re.compile(
                r"loan-profiles-v1/(\d+)/"
            ).findall(
                request._request.path
            )[0]
        except IndexError:
            # Maybe it is better to raise an exception,
            # because this permission must be used with
            # specific url of view.
            return not self.limitation_enabled
        try:
            loan_profile_obj = LoanProfileV1.objects.get(id=loan_profile_id)
        except LoanProfileV1.DoesNotExist:
            return not self.limitation_enabled
        return self._perform_check(request, loan_profile_obj)


class LoanProfileModifyOperationsPermission(ModifyOperationsPermission):
    """
    Used for loan profile view, to prevent several requests
    to get loan profile object since it will be passed
    to has_object_permission().
    """

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return self._perform_check(request, obj)
