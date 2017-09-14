# -*- coding: utf-8 -*-

from decimal import Decimal
import math
import re

from django.contrib.postgres.fields.array import ArrayField
from django.core import exceptions
from django.utils.encoding import force_text
from django.utils.translation import string_concat
from rest_framework import serializers


#####################
# serializer fields #
#####################
class NativeField(serializers.Field):
    def to_internal_value(self, obj):
        return obj

    def to_representation(self, value):
        return value


class MaskedField(serializers.Field):
    def to_representation(self, obj):
        def _masked_length(value):
            SAFE_SUMMARY_DEFAULT_LEN_MAX = 4
            SAFE_SUMMARY_DEFAULT_PCT_MAX = Decimal(0.5)
            return (SAFE_SUMMARY_DEFAULT_LEN_MAX
                    if value == ''
                    else int(min(SAFE_SUMMARY_DEFAULT_LEN_MAX,
                                 math.floor(SAFE_SUMMARY_DEFAULT_PCT_MAX * len(value)))))
        if not obj or not isinstance(obj, basestring):
            return obj
        mask_value = obj[:1 + _masked_length(obj)]
        if not mask_value:
            return obj
        masked_value = u'• ' * len(mask_value)
        return force_text(obj).replace(mask_value, masked_value)

    def to_internal_value(self, data):
        return data


class SsnDashedField(serializers.CharField):
    SSN_RE = r'^\d{3}-\d{2}-\d{4}$'

    def to_representation(self, value):
        if value:
            value = '***-**-{}'.format(str(value)[-4:])
        return super(SsnDashedField, self).to_representation(value)

    def to_internal_value(self, data):
        if data and not re.match(self.SSN_RE, data):
            raise serializers.ValidationError('Incorrect format. Expected `XXX-XX-XXXX`.')
        return super(SsnDashedField, self).to_internal_value(data)


class SsnDigitsField(serializers.CharField):
    SSN_RE = r'^\d{9}$'

    def to_representation(self, value):
        if value:
            value = '*****{}'.format(str(value)[-4:])
        return super(SsnDigitsField, self).to_representation(value)

    def to_internal_value(self, data):
        if data:
            if not re.match(self.SSN_RE, data):
                raise serializers.ValidationError('Incorrect format. Expected `XXXXXXXXX`.')
            data = '{}-{}-{}'.format(data[0:3], data[3:5], data[5:])
        return super(SsnDigitsField, self).to_internal_value(data)


################
# model fields #
#################
class CustomArrayField(ArrayField):
    """
    created to allow the setting of `default=[]` AND `blank=False`

    django, by default recognizes `[]` as a "blank"/"empty" field.  removing `[]` from
    the default empty_values, fixes this problem.
    """
    empty_values = (None, '', (), {})  # excludes []

    def to_python(self, value):
        """
        add an early return for empty values, otherwise this method breaks.

        original method:
            if isinstance(value, six.string_types):
                vals = json.loads(value)  # THIS LINE WOULD BREAK ON AN EMPTY VALUE like ''
                value = [self.base_field.to_python(val) for val in vals]
            return value
        """
        # TODO: remove override if source code is fixed
        if value in self.empty_values:
            return value
        return super(CustomArrayField, self).to_python(value)

    def validate(self, value, model_instance):
        """override to fix error in source"""
        # TODO: remove override if source code is fixed
        # pylint: disable=bad-super-call
        super(ArrayField, self).validate(value, model_instance)
        for i, part in enumerate(value):
            try:
                self.base_field.validate(part, model_instance)
            except exceptions.ValidationError as e:
                raise exceptions.ValidationError(
                    # this line is the problem, is e.message in source django 1.9.7
                    string_concat(self.error_messages['item_invalid'], e.messages),
                    code='item_invalid',
                    params={'nth': i},
                )
        if isinstance(self.base_field, ArrayField):
            if len({len(i) for i in value}) > 1:
                raise exceptions.ValidationError(
                    self.error_messages['nested_array_mismatch'],
                    code='nested_array_mismatch',
                )
