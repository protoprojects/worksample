from django.utils import six

from rest_framework import fields
from rest_framework.fields import empty


class NullableMixin(object):
    """
    If django ChardField or TextField
    is blank=True and not null=True,
    need to convert nulls to empty string
    to prevent validation error.
    """

    def get_value(self, dictionary):
        val = dictionary.get(self.field_name, empty)
        if val is None:
            dictionary[self.field_name] = six.text_type()
        return super(NullableMixin, self).get_value(dictionary)


class NullableCharField(NullableMixin, fields.CharField):
    pass


class NullableEmailField(NullableMixin, fields.EmailField):
    pass
