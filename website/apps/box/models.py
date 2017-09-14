from django.db import models

from core.models import TimeStampedModel

from model_utils import Choices


class BoxEvent(TimeStampedModel):
    BOX_EVENT_TYPE_CHOICES = Choices(
        ('uploaded', 'Uploaded'),
        ('deleted', 'Deleted'),
    )

    box_event_type = models.CharField(max_length=20, choices=BOX_EVENT_TYPE_CHOICES, db_index=True)
    is_processed = models.BooleanField(default=False)
    storage = models.ForeignKey('storage.Storage', related_name='+')
    # ID of document on the Box side
    document_id = models.CharField(max_length=255)
    box_user_id = models.CharField(max_length=255)
    user = models.ForeignKey('accounts.User', null=True, blank=True)

    def __str__(self):
        return "id: {}, event type: {}".format(self.id, self.box_event_type)

    def save(self, *args, **kwargs):
        super(BoxEvent, self).save(*args, **kwargs)
        self.run_processing()

    def run_processing(self):
        if not self.is_processed:
            from .tasks import delete_document_by_box_event, create_document_by_box_event

            if self.box_event_type == self.BOX_EVENT_TYPE_CHOICES.deleted:
                delete_document_by_box_event.delay(self.id)
            elif self.box_event_type == self.BOX_EVENT_TYPE_CHOICES.uploaded:
                create_document_by_box_event.delay(self.id)
