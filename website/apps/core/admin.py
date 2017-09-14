from django.contrib import admin

from solo.admin import SingletonModelAdmin

from core import models as core_models


class JustWatchModelAdminMixin(object):
    # pylint: disable=no-self-use
    def has_delete_permission(self, request, obj=None):
        return False

    # pylint: disable=no-self-use
    def has_add_permission(self, request, obj=None):
        return False


class CustomModelAdmin(admin.ModelAdmin):
    """
    dy default:
    - makes all fields read only (add field to "editable_fields" to make editable)
    - limits all actions to: mark_inactive and mark_active
    """

    actions_on_top = True  # controls where on the page the actions bar appears
    actions_on_bottom = False
    actions = ['mark_inactive', 'mark_active']
    editable_fields = []

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        all_fields = (set(admin.utils.flatten_fieldsets(self.fieldsets))
                      if self.fieldsets
                      else {field.name for field in self.opts.local_fields + self.opts.local_many_to_many})
        return list(all_fields - set(self.editable_fields))

    def mark_inactive(self, request, queryset):  # pylint: disable=no-self-use
        queryset.update(is_active=False)

    def mark_active(self, request, queryset):  # pylint: disable=no-self-use
        queryset.update(is_active=True)


class MaskFieldsMixin(object):
    """
    A mixin that can be used for mask fields

    _field_view_prefix: Default attribute. Used for define new field name
    mask_fields: List of fields that should be masked
    """
    _field_view_prefix = 'view_'
    mask_fields = []

    def _mask_fields(self, fields):
        """
        Changes field name if it is specified in mask_fields

        :param fields: list of field names
        :type fields: list
        :return: modified list of field names
        :rtype: list
        :raises NotImplementedError: Raise if field name was defined in mask_fields but "view_field_name" method
                                     not implemented.
        """
        for i, field in enumerate(fields):
            if field in self.mask_fields:
                field_view = '{}{}'.format(self._field_view_prefix, field)
                if not hasattr(self, field_view):
                    msg = 'Field {} was set in mask_fields. Method {} should be implemented.'.format(field, field_view)
                    raise NotImplementedError(msg)
                fields[i] = field_view
        return fields

    def get_readonly_fields(self, request, obj=None):
        fields = list(super(MaskFieldsMixin, self).get_readonly_fields(request, obj))
        fields = self._mask_fields(fields)
        return fields

    def get_fields(self, request, obj=None):
        fields = list(self.get_readonly_fields(request, obj))
        fields = self._mask_fields(fields)
        return fields

    def get_list_display(self, request):
        fields = list(super(MaskFieldsMixin, self).get_list_display(request))
        fields = self._mask_fields(fields)
        return fields


admin.site.disable_action('delete_selected')  # this disables the action globally...
admin.site.register(core_models.OfficeAddress, SingletonModelAdmin)
admin.site.register(core_models.EncompassSync, SingletonModelAdmin)
admin.site.register(core_models.Recaptcha, SingletonModelAdmin)
