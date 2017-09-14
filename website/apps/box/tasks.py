import logging

from celery.exceptions import Retry

from box.api_v1 import box_file_get
from box.models import BoxEvent
from encompass.client import EncompassClient
from storage.tasks import send_document_to_encompass
from storage.models import Document, DocumentType
from core.utils import SynchronousTask

logger = logging.getLogger('sample.box.tasks')


class DeleteDocumentByBoxEvent(SynchronousTask):
    """
    Processing delete document event from BOX UI.
    """
    def synchronous_run(self, box_event_id):
        logger.debug('PROCESSING-BOX-DELETE-DOCUMENT-EVENT event_id %s.', box_event_id)
        event = BoxEvent.objects.get(id=box_event_id)

        document = Document.objects.get(document_id=event.document_id)
        document.is_deleted = True
        document.deleted_by = event.user
        document.save(update_fields=['is_deleted', 'deleted_by'])
        logger.info('BOX-DELETE-EVENT-COMPLETED event_id %s.', box_event_id)

        event.is_processed = True
        event.save(update_fields=['is_processed'])


class SyncUnprocessedBoxEvents(SynchronousTask):
    use_args_in_lock_key = False

    def synchronous_run(self, offset_event_id=None, limit=1000):
        """
        Run processing for unprocessed box events

        :param offset_event_id: event id
        It is necessary to make offset for unprocessed objects and
        be sure that the processing of the previous objects does not affect the next fetching

        :param limit: limit fetch objects in one task
        """
        filter_queryset = {'is_processed': False}
        if offset_event_id:
            filter_queryset['id__gt'] = offset_event_id
        events = BoxEvent.objects.filter(**filter_queryset).order_by('id')[:limit]
        if events.exists():
            for event in events:
                event.run_processing()
            sync_unprocessed_box_events.delay(offset_event_id=event.id, limit=limit)


class CreateDocumentByBoxEvent(SynchronousTask):
    """
    Processing create or update document event from BOX UI.
    """

    _log_prefix = 'CREATE-DOCUMENT-BY-BOX-EVENT-TASK'

    def synchronous_run(self, box_event_id):
        logger.info('%s-START box event id: %s', self._log_prefix, box_event_id)
        box_event = BoxEvent.objects.get(id=box_event_id)

        # retry to process current event later if
        # there are documents with transmission status in progress
        # note: documents in related storage only
        self._retry_later_if_related_documents_are_processing(box_event)

        box_file = box_file_get(box_event.document_id).get()
        document = self._get_or_initialize_document(box_event)
        document.name = box_file.name
        document.checksum = box_file.sha1
        document.save()

        lp = box_event.storage.get_loan_profile()
        if lp and lp.is_encompass_synced:
            # submit attachment to Encompass if loan has been already synced
            send_document_to_encompass.delay(document.id)

        box_event.is_processed = True
        box_event.save(update_fields=['is_processed'])
        logger.info('%s-FINISH box event id: %s; document: %s', self._log_prefix,
                    box_event_id, document.__repr__())

    @staticmethod
    def _get_or_initialize_document(event):
        try:
            document = Document.objects.get(document_id=event.document_id, storage=event.storage)
        except Document.DoesNotExist:
            document = Document(
                storage=event.storage,
                document_id=event.document_id,
                transmission_status=Document.TRANSMISSION_RECEIPT,
                document_type=DocumentType.objects.get_default()
            )
        return document

    def _retry_later_if_related_documents_are_processing(self, box_event):
        if Document.objects.filter(transmission_status=Document.TRANSMISSION_INPROGRESS,
                                   storage=box_event.storage).exists():
            msg = ('Event: {} can\'t be processed now '
                   'since related documents are processing. '
                   'Will retry in 15 sec.').format(box_event.__repr__())
            logger.info('%s %s', self._log_prefix, msg)
            # raise provided exception and
            # retry to process current event again in 15 seconds
            self.retry(countdown=15, exc=Retry(msg))


delete_document_by_box_event = DeleteDocumentByBoxEvent()
sync_unprocessed_box_events = SyncUnprocessedBoxEvents()
create_document_by_box_event = CreateDocumentByBoxEvent()
