import logging
import mock

from django.test import override_settings
from celery.exceptions import Retry

from core.utils import LogMutingTestMixinBase
from core.tests import CeleryTaskTestCase
from box.tasks import (CreateDocumentByBoxEvent, logger as box_tasks_logger)
from storage.models import Document
from storage import factories as storage_factories
from box import factories as box_factories
from box.models import BoxEvent


class BoxTasksLogMutingMixin(LogMutingTestMixinBase):
    log_names = [box_tasks_logger.name]
    mute_level = logging.CRITICAL


class CreateDocumentByBoxEventTaskTest(BoxTasksLogMutingMixin, CeleryTaskTestCase):
    def setUp(self):
        super(CreateDocumentByBoxEventTaskTest, self).setUp()
        self.patcher = mock.patch('box.models.BoxEvent.run_processing')
        self.run_processing_mock = self.patcher.start()
        self.task = CreateDocumentByBoxEvent()

    def tearDown(self):
        self.patcher.stop()

    def test_use_args_in_lock_key_is_defined(self):
        self.assertIs(self.task.use_args_in_lock_key, True)

    def test_get_or_initialize_document_without_existing_document(self):
        box_event = box_factories.BoxEventFactory()
        document = self.task._get_or_initialize_document(box_event)
        self.assertEqual(box_event.storage, document.storage)
        self.assertEqual(box_event.document_id, document.document_id)
        self.assertIsNone(document.id)  # is initialized

    def test_get_or_initialize_document_with_existing_document(self):
        document = storage_factories.DocumentFactory()
        box_event = box_factories.BoxEventFactory(storage=document.storage, document_id=document.document_id)
        self.assertEqual(document, self.task._get_or_initialize_document(box_event))

    @override_settings(CELERY_ALWAYS_EAGER=False)
    def test_retry_later_if_related_documents_are_processing(self):
        document = storage_factories.DocumentFactory(transmission_status=Document.TRANSMISSION_INPROGRESS)
        box_event = box_factories.BoxEventFactory(storage=document.storage,
                                                  document_id=document.document_id,
                                                  box_event_type=BoxEvent.BOX_EVENT_TYPE_CHOICES.uploaded)
        with self.assertRaises(Retry):
            self.task._retry_later_if_related_documents_are_processing(box_event)

    @override_settings(CELERY_ALWAYS_EAGER=False)
    def test_retry_later_if_related_documents_are_processing_ignored(self):
        document = storage_factories.DocumentFactory(transmission_status=Document.TRANSMISSION_RECEIPT)
        box_event = box_factories.BoxEventFactory(storage=document.storage,
                                                  document_id=document.document_id,
                                                  box_event_type=BoxEvent.BOX_EVENT_TYPE_CHOICES.uploaded)
        self.assertIsNone(self.task._retry_later_if_related_documents_are_processing(box_event))
