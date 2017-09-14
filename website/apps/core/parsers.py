import json
import logging
import re
import six

from django.http import QueryDict

from rest_framework.exceptions import ParseError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from django.conf import settings

logger = logging.getLogger("sample.core.parsers")

first_cap_re = re.compile('(.)([A-Z][a-z])')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def camel_to_underscore(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def underscoreize(data):
    '''Recursively convert camelcase data to underscore

    Requires all dictionary keys to be strings

    Maps tuples to lists but the usage (json, xmltodict) does not
    seem to use tuples. This belief is supported by the fact the
    previous code would have thrown a TypeError.

    '''
    # TODO: Add Error handling. Only dict, tuple and list are checked. Other objects are not caught.
    if isinstance(data, dict):
        retval = {camel_to_underscore(key): underscoreize(value)
                  for key, value in data.items()}
    elif isinstance(data, (list, tuple)):
        retval = [underscoreize(item) for item in data]
    else:
        retval = data
    return retval


class CamelCaseJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        try:
            data = stream.read().decode(encoding)
            retval = underscoreize(json.loads(data))
        except ValueError as exc:
            raise ParseError('JSON parse error - {}'.format(six.text_type(exc)))
        return retval


class CamelCaseMultiPartParser(MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data_and_files = super(CamelCaseMultiPartParser, self).parse(stream, media_type, parser_context)

        data = underscoreize(data_and_files.data.dict())
        data_and_files.data.clear()
        data_and_files.data.update(data)
        return data_and_files


class CamelCaseFormParser(FormParser):
    """Parses camelCase to snake_case for urlencoded requests."""
    media_type = 'application/x-www-form-urlencoded'

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        try:
            query_dict = QueryDict(stream.read(), encoding=encoding)
            data = underscoreize(query_dict)
        except Exception as exc:
            logger.exception("CAMELCASE-PARSE-ERROR: %s data %s", exc, stream)
            raise ParseError("CamelCaseFormParser error: %s", exc)
        else:
            logger.info("CAMELCASE-PARSE-SUCCESS: %s", data)
            return data
