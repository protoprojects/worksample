import logging
import mock

from rest_framework import status
from factory import fuzzy

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings

from accounts import factories as account_factories
from box.models import BoxEvent
from box.views import BoxEventCallback
from box.permissions import BoxEventCallbackPermission
from storage.models import Document, Storage
from storage import factories as storage_factories


logger = logging.getLogger('sample.box.tests.box_event_callback')


@override_settings(CELERY_ALWAYS_EAGER=True)
class CreateBoxEventTestCase(TestCase):
    @staticmethod
    def _get_box_file_mock():
        test_box_file_mock = mock.MagicMock()
        test_box_file_data = {
            'name': 'fileName.doc',
            'sha1': 'test-sha1',
            'object_id':'777',
            'content': lambda: 'file-test-content',
            'get': lambda: test_box_file_mock
        }
        test_box_file_mock.configure_mock(**test_box_file_data)
        return test_box_file_mock

    def setUp(self):
        super(CreateBoxEventTestCase, self).setUp()
        fuzzy_integer = fuzzy.FuzzyInteger(1, 10**10)

        self.url = reverse('box_event_callback')
        self.document_tags = storage_factories.DocumentTagFactory.create_batch(6)
        self.document_type = storage_factories.DocumentTypeFactory()
        self.advisor = account_factories.AdvisorFactory()
        self.customer = account_factories.CustomerFactory(advisor=self.advisor)

        mock_box_folder = mock.MagicMock(object_id=fuzzy_integer.fuzz())
        mock_box_parent_folder = mock.MagicMock(object_id=fuzzy_integer.fuzz())

        self.storage = Storage.objects.create_documents_storage(
            mock_box_folder, mock_box_parent_folder, name=fuzzy.FuzzyText().fuzz()
        )

        self.box_uploaded_event_data = {
            'item_id': str(fuzzy_integer.fuzz()),
            'from_user_id': str(fuzzy_integer.fuzz()),
            'token': settings.BOX_API_OAUTH_CLIENT_ID,
            'item_parent_folder_id': self.storage.storage_id,
            'event_type': BoxEvent.BOX_EVENT_TYPE_CHOICES.uploaded
        }
        self.box_deleted_event_data = self.box_uploaded_event_data.copy()
        self.box_deleted_event_data['event_type'] = BoxEvent.BOX_EVENT_TYPE_CHOICES.deleted

    def test_view_permissions_are_in_place(self):
        self.assertEqual(BoxEventCallback.permission_classes, (BoxEventCallbackPermission,))

    @mock.patch('box.views.BoxEventCallback._handle_errors')
    def test_view_permissions(self, mocked_handle_errors):
        # request without token
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # request with wrong token
        resp = self.client.get(self.url, data={'token': 'wrong_token'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # request with correct token
        resp = self.client.get(self.url, data={'token': settings.BOX_API_OAUTH_CLIENT_ID})
        self.assertNotEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_event_with_not_existing_storage_should_be_ignored(self):
        data = self.box_uploaded_event_data
        data['item_parent_folder_id'] = 'some-not-existing-id'
        resp = self.client.get(self.url, data=data)
        self.assertEqual(BoxEvent.objects.count(), 0)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    @mock.patch('box.views.BoxEventCallback._handle_errors')
    def test_if_event_is_empty(self, mocked_handle_errors):
        resp = self.client.get(self.url, data={'token': settings.BOX_API_OAUTH_CLIENT_ID})
        # return status should be success even
        # if required data has not been provided
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    @mock.patch("storage.models.Storage.get_loan_profile")  # used in celery task
    @mock.patch("box.tasks.box_file_get")
    def test_uploaded_event_processed_successful(self, mock_box_file_get, mock_get_loan_profile):
        data = self.box_uploaded_event_data
        mock_box_file_get.return_value = self._get_box_file_mock()
        mock_get_loan_profile.return_value = None
        resp = self.client.get(self.url, data=data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # all required instances has been craeted
        self.assertEqual(BoxEvent.objects.count(), 1)
        self.assertEqual(Document.objects.count(), 1)

        # check all data has been saved properly
        document = Document.objects.first()
        box_event = BoxEvent.objects.first()
        self.assertEqual(document.document_id, data['item_id'])
        self.assertEqual(document.name, self._get_box_file_mock().name)
        self.assertEqual(box_event.document_id, data['item_id'])
        self.assertEqual(box_event.box_event_type, BoxEvent.BOX_EVENT_TYPE_CHOICES.uploaded)
        self.assertEqual(box_event.is_processed, True)

    def test_deleted_event_processed_successful(self):
        data = self.box_deleted_event_data
        # document instance should be created at first
        storage_factories.DocumentFactory.create(storage=self.storage,
                                                 document_id=data['item_id'],
                                                 document_type=self.document_type)
        self.assertEqual(Document.objects.count(), 1)
        resp = self.client.get(self.url, data=data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # all required instances has been craeted
        self.assertEqual(BoxEvent.objects.count(), 1)
        self.assertEqual(Document.objects.count(), 1)

        # check all data has been updated properly
        document = Document.objects.first()
        box_event = BoxEvent.objects.first()
        self.assertEqual(document.is_deleted, True)
        self.assertEqual(box_event.document_id, data['item_id'])
        self.assertEqual(box_event.box_event_type, BoxEvent.BOX_EVENT_TYPE_CHOICES.deleted)
        self.assertEqual(box_event.is_processed, True)
