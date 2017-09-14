'''
Main module for the rate quote tool. This forms Mortech API requests and returning the response. MortechAPI
sends the request and receives an XML response.
The response is parsed to dictionary format and stored in RateQuoteLender.

See the README.md for this app for more details.

Mortech documentation: https://sample.box.com/mortech-api-documentation
'''

import copy
import logging

from decimal import Decimal
from lxml import etree
import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout, RequestException

from django.conf import settings
from core.utils import memoize
from mortgage_profiles.models import MortgageProfile, RateQuoteLender, RateQuoteRequest
from mortgage_profiles.mortech.calculations import (
    MortechCalculations, MortechCalculationsPurchase, MortechCalculationsRefinance)
from mortgage_profiles.utils import (
    MortechXMLParser, get_lender_fees, get_term, get_program_type)

logger = logging.getLogger('sample.mortech.api')


class MortechApi(object):
    '''
    Map from mortgage profile model to Mortech API request.
    '''

    MORTECH_ENDPOINT = settings.MORTECH_ENDPOINT
    SAVE_MORTECH_RESPONSE = settings.SAVE_MORTECH_RESPONSE

    MORTECH_KINDS = {
        MortgageProfile.PURCHASE: MortechCalculationsPurchase,
        MortgageProfile.REFINANCE: MortechCalculationsRefinance,
    }

    def __init__(self, mortgage_profile):
        self.instance = mortgage_profile
        self.calculations = self.get_calculations()

    def get_calculations(self):
        '''Return Mortech calculation object based on mortgage profile kind.'''
        mortech_calculations = self.MORTECH_KINDS[self.instance.kind]
        return mortech_calculations(self.instance)

    @memoize
    def get_initial_data(self):
        '''
        Return user data from mortgage_profile to form a Mortech request.
        Hard-coded default parameters below are used for Rate Quote Tool results and the disclaimer.
        '''
        # Best Offer Strategy
        return {
            'licenseKey': settings.MORTECH_LICENSEKEY,
            'thirdPartyName': settings.MORTECH_THIRDPARTY_NAME,
            'customerId': settings.MORTECH_CUSTOMER_ID,
            'emailAddress': settings.MORTECH_EMAIL,
            'request_id': 1,
            'propertyState': self.calculations.get_property_state_code(),
            'propertyCounty': self.calculations.get_county(),
            'loan_amount': self.calculations.get_loan_amount(),
            'fico': self.instance.credit_score,
            'propType': self.calculations.get_property_type(),
            'loanpurpose': self.calculations.get_loan_purpose(),
            'occupancy': self.calculations.get_occupancy_type(),
            'targetPrice': '-999',  # Returns everything for the above products.
            'pmiCompany': '-999',   # includes monthlyPremium for mortgage insurance
            'lockindays': '45',
            'appraisedvalue': self.instance.get_property_value(),
            'loanProduct1': '30 year fixed',
            'loanProduct2': '15 year fixed',
            'loanProduct3': '7 year ARM/30 yrs',
            'loanProduct4': '5 year ARM/30 yrs',
        }

    def build_request_data(self):
        '''Return Mortech request.'''
        initial_data = {k: v for k, v in self.get_initial_data().items() if v is not None}

        logger.debug(u'BUILD-REQUEST-DATA %s profile %s user %s',
                     initial_data, self.instance.get_kind_display(), self.instance.user)

        debug_data = copy.copy(initial_data)

        # Debugging API
        del debug_data['licenseKey']
        del debug_data['thirdPartyName']
        del debug_data['customerId']
        del debug_data['emailAddress']
        self.instance.initial_data = debug_data
        self.instance.debug_data = copy.copy(debug_data)

        return initial_data

    @memoize
    def is_valid(self):
        return all([
            self.calculations.is_enough_data(),
            self.calculations.is_valid_state()
        ])

    def get_errors(self):
        status = {
            'is_enough_data': self.calculations.is_enough_data(),
            'is_valid_state': self.calculations.is_valid_state()
        }
        errors = {'errors': dict((k, v) for k, v in status.items() if v is False)}
        return errors

    def get_filter_ids(self):
        """
        Filters results from Mortech API and returns the filtered items.
        Filters are exclusive and they do not stack. Only 1 can be applied per request.

        - FHA: Returns exclusively FHA products.
        - VA: Returns exclusively VA products, even if user qualifies for non-VA products.
        - '': No filter.

        More filters can be configured at the Mortech admin panel online.
        """
        filter_ids = ['', '888888']
        if self.instance.is_veteran:
            filter_ids.insert(0, '999999')
        return filter_ids

    def get_response(self):
        """Return Mortech API response."""
        for filter_id in self.get_filter_ids():
            request_data = self.build_request_data()
            request_data['filterId'] = filter_id
            try:
                response = requests.post(self.MORTECH_ENDPOINT, params=request_data, timeout=90)
                response.raise_for_status()
            except Timeout, exc:
                logger.exception("MORTECH-REQUEST-TIMEOUT %s", exc)
                raise
            except ConnectionError, exc:
                logger.exception("MORTECH-REQUEST-CONNECTIONERROR %s", exc)
                raise
            except HTTPError, exc:
                logger.exception("MORTECH-REQUEST-HTTPERROR %s", exc)
                raise
            except RequestException, exc:
                logger.exception("MORTECH-REQUEST-REQUESTEXCEPTION %s", exc)
                raise
            else:
                if not response.content:
                    logger.debug("MORTECH-GET-RESPONSE-NO-CONTENT req headers %s, res headers %s",
                                 response.headers, response.request.headers)
                    raise Exception("Mortech response is missing content.")

            self.save_response(self.instance.initial_data, filter_id, response.content)
            xml = etree.fromstring(response.content)
            result_count = sum([int(item) for item in xml.xpath('//results/@size')])
            if 0 < result_count:
                logger.debug('MORTECH-GET-RESPONSE-SUCCESS filter "%s" count %s',
                             filter_id, result_count)
                xml = None
                break
            else:
                logger.info('MORTECH-GET-RESPONSE-SKIP filter "%s" count %s',
                            filter_id, result_count)
        else:
            logger.debug('MORTECH-GET-RESPONSE-FAILED')

        # Update rate quote refresh flag to in_progress
        self.instance.update_refresh_status(self.instance.REFRESH_PROGRESS_CHOICES.in_progress)
        logger.info('MORTECH-RATE-QUOTE-STATUS id %s, Progress %s',
                    self.instance.id,
                    self.instance.rate_quote_refresh_progress)

        parsed_response = self.parse_xml(response.content)
        if parsed_response.has_results:
            self.save_lenders(parsed_response)
        return parsed_response

    def save_response(self, req, filter_id, response):
        if self.SAVE_MORTECH_RESPONSE:
            try:
                filename = mortech_request_to_filename(req, filter_id, path='/tmp/')
                with open(filename, 'w') as response_file:
                    response_file.write(response)
            except IOError as exc:
                logger.debug(u'SAVE-MORTECH-RESPONSE-FAILED %s', exc)
        logger.info(u'MORTECH-RESPONSE-RECV profile %s user %s',
                    self.instance.get_kind_display(), self.instance.user)

    @staticmethod
    def parse_xml(response):
        xml_parser = MortechXMLParser()
        return xml_parser.parse(response)

    def save_lenders(self, mortech_response):
        """Takes api response, consumes lender data and saves to db."""
        rate_quote_request = RateQuoteRequest.objects.create(mortgage_profile=self.instance)

        lenders_for_bulk = []
        results = mortech_response.response.get('results')
        if not results:
            logger.info('MORTECH-NO-RESULTS-FOUND rate_quote_request %s credit_score %s ltv %s',
                        rate_quote_request.id,
                        self.instance.credit_score,
                        self.instance.get_loan_to_value())
            return
        else:
            if not isinstance(results, (list, tuple)):
                results = [results]
            for item in results:
                quotes = item.get('quote', ())
                if not isinstance(quotes, (list, tuple)):
                    quotes = [quotes]

                for quote in quotes:
                    fees = get_lender_fees(quote['quote_detail']['fees']['fee_list']['fee'])
                    term = get_term(quote)
                    program_type = get_program_type(quote['@vendor_product_name'], item['@product_name'])
                    rate = Decimal(quote['quote_detail']['@rate']) * Decimal(100.0)

                    lender = RateQuoteLender(
                        request=rate_quote_request,
                        lender_name=quote['@vendor_name'],
                        term=term,
                        amortization_type=item['@term_type'],
                        program_category=item['@product_name'],
                        program_name=quote['@vendor_product_name'],
                        program_type=program_type,
                        points=Decimal(quote['quote_detail']['@price']),
                        price=Decimal(quote['quote_detail']['ratesheet_price']),
                        rate=rate,
                        monthly_premium=Decimal(quote['quote_detail']['@monthly_premium']),
                        piti=Decimal(quote['quote_detail']['@piti']),
                        upfront_fee=Decimal(quote['quote_detail']['@upfront_fee']),
                        apr=Decimal(quote['quote_detail']['@apr']),
                        fees=fees
                    )
                    lenders_for_bulk.append(lender)

            lenders_list = RateQuoteLender.objects.bulk_create(lenders_for_bulk)

            logger.info(
                "%d Lenders saved to db for Profile: %s, User: %s.",
                len(lenders_list),
                self.instance.get_kind_display(),
                self.instance.user)

            # Update rate quote refresh status to complete
            self.instance.update_refresh_status(self.instance.REFRESH_PROGRESS_CHOICES.complete)
            logger.debug('MORTECH-RATE-QUOTE-STATUS id %s, Progress %s',
                         self.instance.id,
                         self.instance.rate_quote_refresh_progress)
            return lenders_list


def mortech_request_to_filename(req, filter_id='', path=''):
    '''Convert a Mortech request into a filename'''
    def identity(key, val):
        return u'{}'.format(val) if val else u'NA'

    def integer_value(key, val):
        fmt = '{}' if isinstance(val, basestring) else '{0:d}'
        return u'NA' if val is None else fmt.format(val)

    def occupancy_type_value(key, val):
        occupancy_types = {
            MortechCalculations.OCCUPANCY_TYPE_OWNER_OCCUPIED: 'OWN',
            MortechCalculations.OCCUPANCY_TYPE_SECOND_HOME: '2ND',
            MortechCalculations.OCCUPANCY_TYPE_NON_OWNER_OCCUPIED: 'INV'}
        return occupancy_types.get(val, 'UNKN')

    def property_type_value(key, val):
        property_types = {
            MortechCalculations.PROPERTY_TYPE_1_UNIT: '1FMA',
            MortechCalculations.PROPERTY_TYPE_2_UNIT: '2UNI',
            MortechCalculations.PROPERTY_TYPE_3_UNIT: '3UNI',
            MortechCalculations.PROPERTY_TYPE_4_UNIT: '4UNI',
            MortechCalculations.PROPERTY_TYPE_CONDOS_LOW: 'CON0',
            MortechCalculations.PROPERTY_TYPE_CONDOS_MID: 'CON5',
            MortechCalculations.PROPERTY_TYPE_CONDOS_HIGH: 'CON8',
            MortechCalculations.PROPERTY_TYPE_TOWNHOMES: 'TWNH',
            MortechCalculations.PROPERTY_TYPE_MANUFACTURED_HOME: 'MANU'}
        return property_types.get(val, 'UNKN')

    def purpose_type_value(key, val):
        purpose_types = {
            MortechCalculations.LOAN_PURPOSE_PURCHASE: 'PUR',
            MortechCalculations.LOAN_PURPOSE_CASHOUT: 'CSH',
            MortechCalculations.LOAN_PURPOSE_RATE_AND_TERM: 'RAT',
            MortechCalculations.LOAN_PURPOSE_HOME_EQUITY: 'EQT',
            MortechCalculations.LOAN_PURPOSE_HELOC: 'HEL'}
        return purpose_types.get(val, 'UNKN')

    def county_value(key, val):
        return val.replace('County', '').strip().replace(' ', '_')

    segments = (('propertyState', identity),
                ('fico', integer_value),
                ('propertyType', property_type_value),
                ('occupancy', occupancy_type_value),
                ('loanpurpose', purpose_type_value),
                ('propertyCounty', county_value),
                ('appraisedValue', integer_value),
                ('loan_amount', integer_value))
    vals = {key: val_fn(key, req.get(key, None))
            for key, val_fn in segments}
    fmt = ('{path}{propertyState}-{fico}-{propertyType}'
           '-{occupancy}-{loanpurpose}'
           '-{propertyCounty}-{appraisedValue}-{loan_amount}-{FilterId}.xml')
    return fmt.format(path=path, FilterId=filter_id, **vals)
