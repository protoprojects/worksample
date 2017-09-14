import factory
import factory.fuzzy
import requests
import json
from datetime import timedelta

from httmock import response, urlmatch, remember_called, all_requests
from boxsdk.exception import BoxAPIException

from django.utils import timezone

from box.models import BoxEvent
from storage.factories import StorageFactory
from storage.settings import LINK_EXPIRATION_DAYS


class BoxEventFactory(factory.DjangoModelFactory):
    class Meta:
        model = BoxEvent

    document_id = factory.fuzzy.FuzzyInteger(1, 10**10)
    box_event_type = factory.fuzzy.FuzzyChoice(choices=BoxEvent.BOX_EVENT_TYPE_CHOICES._db_values)
    storage = factory.SubFactory(StorageFactory)


@urlmatch(scheme='https', netloc='api.box.com', path='/2.0/files/11111', method='put')
@remember_called
def box_response_status_code_503(url, request):
    if box_response_status_code_503.call['count'] > 0:
        raise BoxAPIException(status=503, code=u'unavailable')

    content = {
        "type": "error",
        "status": 503,
        "code": "unavailable",
        "help_url": "http://developers.box.com/docs/#errors",
        "message": "Unavailable",
        "request_id": "2662633357555f584de87b9"
    }
    return response(503, content, elapsed=0, request=request)


@urlmatch(scheme='https', netloc='api.box.com', path='/2.0/files/11111', method='put')
@remember_called
def box_response_status_code_429(url, request):
    if box_response_status_code_429.call['count'] > 0:
        raise BoxAPIException(status=429, code=u'rate_limit_exceeded')

    content = {
        "type": "error",
        "status": 429,
        "code": "rate_limit_exceeded",
        "help_url": "http://developers.box.com/docs/#errors",
        "message": "Request rate limit exceeded, please try again later",
        "request_id": "2662633357555f584de87b9"
    }
    headers = {'Retry-After': 0.1}
    return response(429, content, headers=headers, elapsed=0, request=request)


@urlmatch(scheme='https', netloc='api.box.com', path='/2.0/files/11111', method='put')
@remember_called
def box_response_status_code_404(url, request):
    content = {
        "type": "error",
        "status": 404,
        "code": "not_found",
        "help_url": "http://developers.box.com/docs/#errors",
        "request_id": "2662633357555f584de87b9"
    }
    return response(404, content, elapsed=0, request=request)


@urlmatch(scheme='https', netloc='api.box.com', path='/2.0/files/11111', method='put')
@remember_called
def box_response_timeout(url, request):
    raise requests.exceptions.Timeout


@all_requests
@remember_called
def box_all_response_status_code_503(url, request):
    raise BoxAPIException(status=503, message=u'unavailable', code=u'unavailable')


@urlmatch(scheme='https', netloc='api.box.com', path='/2.0/files/135876865413', method='put')
@remember_called
def box_file_135876865413_shared_link(url, request):
    unshared_at = json.loads(request.body).get('shared_link', {}).get('unshared_at', None)
    assert unshared_at is not None, 'Not received unshared_at value'
    unshared_date = timezone.datetime.strptime(unshared_at, '%Y-%m-%dT%H:%M:%S.%f')
    current_unshared_date = timezone.datetime.today() + timedelta(days=LINK_EXPIRATION_DAYS)
    diff_date = current_unshared_date - unshared_date
    assert diff_date.total_seconds() < 10, 'Not a valid value unshared_at'
    content = {
        "type": "file",
        "id": "135876865413",
        "etag": "1",
        "shared_link": {
            "url": "https://sample.box.com/s/ace7rmaz67t7ah86hk6ocppo1y4q4gon",
            "download_url": "https://sample.box.com/shared/static/ace7rmaz67t7ah86hk6ocppo1y4q4gon.txt",
            "vanity_url": None,
            "effective_access": "company",
            "is_password_enabled": False,
            "unshared_at": unshared_at,
            "download_count": 0,
            "preview_count": 0,
            "access": "company",
            "permissions": {"can_preview": True, "can_download": True}
        },
    }
    return response(200, content, elapsed=0, request=request)
