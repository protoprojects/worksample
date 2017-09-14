from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException


class VirusFound(Exception):
    """Raise is viruses has been found"""
    pass


class ServiceUnavailableException(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _('Service temporarily unavailable.')
    default_code = 'service_unavailable'


class ServiceInternalErrorException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _('Please contact support.')
    parent_exc = None

    def __init__(self, detail=None, code=None, parent_exc=None):
        self.parent_exc = parent_exc
        super(ServiceInternalErrorException, self).__init__(detail=detail, code=code)
