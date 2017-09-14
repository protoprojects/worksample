from rest_framework import serializers

from box.api_v1 import CUSTOMER_DOCUMENTS_STORAGE_ROLE
from storage.models import Storage
from .models import BoxEvent


class BoxEventStorageField(serializers.Field):
    """Custom serializer field to provide storage instance based on `storage_id` field"""

    def to_internal_value(self, data):
        try:
            # Filter customer only storages.
            # We shoudn't store not related to customer's folder events.
            # It's important to use `storage_id` as argument name, not `id`
            return Storage.objects.filter(role=CUSTOMER_DOCUMENTS_STORAGE_ROLE).get(storage_id=data)
        except Storage.DoesNotExist as exc:
            raise serializers.ValidationError(exc.message)


class BoxEventModelSerializer(serializers.ModelSerializer):
    event_type = serializers.ChoiceField(source='box_event_type',
                                         choices=BoxEvent.BOX_EVENT_TYPE_CHOICES)
    from_user_id = serializers.CharField(source='box_user_id')
    item_id = serializers.CharField(source='document_id')
    item_parent_folder_id = BoxEventStorageField(source='storage')

    class Meta:
        model = BoxEvent
        fields = ('event_type', 'from_user_id', 'item_id', 'item_parent_folder_id',)
