from importlib import import_module

from django.conf import settings
from django.test import Client

from rest_framework.test import APIClient

from accounts.tests.helpers import JWTAuthAPITestCase


class AdvisorClient(APIClient):
    def get(self, path, data=None, follow=False, **extra):
        extra['HTTP_X_FOR_UPDATE'] = 1
        return super(AdvisorClient, self).get(
            path=path, data=data, follow=follow, **extra
        )

    # pylint: disable=redefined-builtin
    def post(self, path, data=None, format=None, content_type=None,
             follow=False, **extra):
        extra['HTTP_X_FOR_UPDATE'] = 1
        return super(AdvisorClient, self).post(
            path=path, data=data, format=format,
            content_type=content_type, follow=follow,
            **extra
        )

    # pylint: disable=redefined-builtin
    def put(self, path, data=None, format=None, content_type=None,
            follow=False, **extra):
        extra['HTTP_X_FOR_UPDATE'] = 1
        return super(AdvisorClient, self).put(
            path=path, data=data, format=format,
            content_type=content_type, follow=follow,
            **extra
        )

    # pylint: disable=redefined-builtin
    def patch(self, path, data=None, format=None, content_type=None,
              follow=False, **extra):
        extra['HTTP_X_FOR_UPDATE'] = 1
        return super(AdvisorClient, self).patch(
            path=path, data=data, format=format,
            content_type=content_type, follow=follow,
            **extra
        )

    # pylint: disable=redefined-builtin
    def delete(self, path, data=None, format=None, content_type=None,
               follow=False, **extra):
        extra['HTTP_X_FOR_UPDATE'] = 1
        return super(AdvisorClient, self).delete(
            path=path, data=data, format=format,
            content_type=content_type, follow=follow,
            **extra
        )


class AdvisorAPITestCase(JWTAuthAPITestCase):
    client_class = AdvisorClient


class AdvisorCRUDTestMixin(object):
    """
    Mixin to be used in testing CRUD API endpoints.
    There are common test cases that need to be implemented.
    """

    def test_successful_create(self):
        raise NotImplementedError()

    def test_creation_without_auth_returns_401(self):
        raise NotImplementedError()

    def test_successful_retrieve(self):
        raise NotImplementedError()

    def test_retrieve_obj_of_another_advisor_returns_404(self):
        raise NotImplementedError()

    def test_retrieve_without_auth_returns_401(self):
        raise NotImplementedError()

    def test_successful_update(self):
        raise NotImplementedError()

    def test_update_without_auth_returns_401(self):
        raise NotImplementedError()

    def test_update_obj_of_another_advisor_returns_404(self):
        raise NotImplementedError()

    def test_successful_delete(self):
        raise NotImplementedError()

    def test_delete_without_auth_returns_401(self):
        raise NotImplementedError()

    def test_delete_obj_of_another_advisor_returns_404(self):
        raise NotImplementedError()

    def test_modifying_object_if_it_was_submitted_to_encompass_returns_405(self):
        raise NotImplementedError()

    def test_object_creation_if_owner_does_not_exist_returns_404(self):
        raise NotImplementedError()


def get_client_with_session():
    client = Client()
    engine = import_module(settings.SESSION_ENGINE)
    s = engine.SessionStore()
    s.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = s.session_key
    return client
