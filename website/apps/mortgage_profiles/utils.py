import logging

from django.utils.xmlutils import SimplerXMLGenerator
from six import StringIO

import xmltodict
from rest_framework.parsers import BaseParser
from rest_framework_xml.renderers import XMLRenderer

from core.parsers import underscoreize
from core.utils import memoize


logger = logging.getLogger("sample.mortgage_profiles.utils")


def underscore_to_camelcase(value):
    def camelcase(value):
        return value.capitalize() if not value.isupper() else value

    return "".join(camelcase(x) if x else '_' for x in value.split("_"))


def camelcasify(data):
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_key = underscore_to_camelcase(key)
            new_dict[new_key] = camelcasify(value)
        return new_dict
    if isinstance(data, (list, tuple)):
        for i in range(len(data)):
            data[i] = camelcasify(data[i])
        return data
    return data


class MortechRenderer(XMLRenderer):
    # pylint: disable=W0221
    def render(self, data, accepted_media_type=None, renderer_context=None, start_element=None):
        '''Renders *obj* into serialized XML'''
        if data is None:
            return ''

        stream = StringIO()

        xml = SimplerXMLGenerator(stream, self.charset)
        xml.startDocument()
        xml.startElement(start_element, {})

        self._to_xml(xml, data)

        xml.endElement(start_element)
        xml.endDocument()
        return stream.getvalue()


class MortechXMLParser(BaseParser):
    '''Convert camelcase XML to underscore dict'''
    def parse(self, stream, media_type=None, parser_context=None):
        try:
            data = underscoreize(xmltodict.parse(stream, force_list=('quote', 'fee',)))
        except Exception as exc: #pylint: disable=broad-except
            logger.warning(u'MORTECH-XML-PARSE-ERROR %s data %s', exc, stream)
        else:
            logger.debug(u'MORTECH-XML-PARSE-SUCCESS %s', data['mortech']['header'])
            return MortechResponse(data['mortech'])


class MortechResponse(object):
    '''Store and manipulate response from Mortech API'''
    def __init__(self, response):
        self.response = response
        self.has_results = 'results' in self.response

    @memoize
    def is_valid(self):
        '''Determine whether response is valid.'''
        status = self.response['header'].get('error_desc')
        logger.info('MORTECH-RESPONSE-STATUS %s', status)
        return self.has_results

    def get_errors(self):
        '''Return response errors.'''
        assert not self.is_valid(), 'Response is valid'
        logger.error(u'MORTECH-INVALID-RESPONSE-ERROR %s', self.response['header'])
        return self.response['header']

    def get_data(self):
        '''Return response results.'''
        return self.response['mortech']['results'] if self.response['results'] else []


def mortech_error_response_factory(error):
    '''Create a mortech error response.'''
    return MortechResponse({'header': {'error_desc': error}})


def get_lender_fees(fee_list):
    '''Retrieve fees from Mortech response object.'''
    fees = {}
    if not isinstance(fee_list, (list, tuple)):
        fee_list = [fee_list]
    for fee in fee_list:
        fees[fee['@description']] = fee['@feeamount']

    return fees


def get_program_type(program_type, product_name):
    """
    returns program for the lender based on program_type or product_type.
    :param program_type: this is provided by Mortech and should be a string
    :param product_name: this is provided by Mortech and should be a string
    :return: string indicating program type
    """
    programs = [
        'VA',
        'FHA',
        'Non Conforming',
        'Non Conf',
        'Conforming',
        'Conf',
        'Jumbo',
        'Non-Agency'
    ]

    for program in programs:
        if program in program_type:
            return program
        elif program in product_name:
            return program
    logger.warning('PROGRAM-TYPE-AND-PRODUCT-NAME-NOT-MATCHED program_type %s'
                   'product_name %s', program_type, product_name)
    return program_type if program_type else "unknown"


def get_term(product):
    term_types = {
        '36': '3 Year',
        '60': '5 Year',
        '84': '7 Year',
        '120': '10 Year'
    }
    for k, v in term_types.iteritems():
        if k in product['@initial_arm_term']:
            return v
    # No white space is needed in this return statement.
    return '{0}Year'.format(product['@product_term'])


def get_quotes(obj):
    quotes = obj.get('quote', ())
    if not isinstance('quotes', (list, tuple)):
        quotes = [quotes]
    return quotes
