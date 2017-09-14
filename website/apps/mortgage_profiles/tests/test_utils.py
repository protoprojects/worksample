import logging

from django.test import TestCase

from core.utils import LogMutingTestMixinBase
from mortgage_profiles import mortech
from mortgage_profiles.factories import MortgageProfilePurchaseFactory
from mortgage_profiles.utils import MortechXMLParser, get_program_type


logger = logging.getLogger('sample.mortech.test')


class MortechMutingMixin(LogMutingTestMixinBase):
    log_names = [
        'sample.mortech.api',
        'sample.mortech.fees',
        'sample.mortech.calculations',
        'sample.mortgage_profiles'
    ]


class MortechResponseTestCase(MortechMutingMixin, TestCase):
    """
    TEST_CASES
    * ERROR_RESPONSE (error.xml) : Return api error for unlicensed state.
    * SINGLE_RESPONSE (single-product.xml) : Return 1 product (30 Fixed) with 2 lenders.
    * BLANK_RESPONSE (blank.xml) : Return no results.
    """
    TEST_CASES = 'website/apps/mortgage_profiles/tests/test_cases/{}'
    ERROR_RESPONSE = TEST_CASES.format('mortech_error.xml')
    SINGLE_RESPONSE = TEST_CASES.format('single_product.xml')
    BLANK_RESPONSE = TEST_CASES.format('blank.xml')

    def setUp(self):
        self.mortgage_profile = MortgageProfilePurchaseFactory(
            property_occupation='my_current_residence')
        self.api = mortech.MortechApi(mortgage_profile=self.mortgage_profile)
        super(MortechResponseTestCase, self).setUp()

    def test_response_has_results(self):
        """Should return whether results are contained in the response."""
        with open(self.ERROR_RESPONSE) as xml:
            parser = MortechXMLParser()
            response = parser.parse(xml)
            self.assertFalse(response.has_results)

    def test_response_is_valid(self):
        """Should return whether results are contained in the response."""
        with open(self.SINGLE_RESPONSE) as xml:
            parser = MortechXMLParser()
            response = parser.parse(xml)
            self.assertTrue(response.is_valid())

    def test_get_errors(self):
        """Should return errors if MortechResponse.is_valid == False"""
        error = {'error_num': '-8', 'error_desc': 'State not enabled for customer account'}
        with open(self.ERROR_RESPONSE) as xml:
            parser = MortechXMLParser()
            response = parser.parse(xml)
            self.assertFalse(response.is_valid())
            self.assertEqual(response.get_errors(), error)


class TestMortgageProfileUtils(MortechMutingMixin, TestCase):
    """Tests functions in utils.py file"""

    def test_get_program_type_returns_correct_value(self):
        """
        Should always return a value, regardless of what is passed in.
        If no match found, should return first argument, and
        if first argument empty then should return 'unknown'.
        """
        program_type = get_program_type('something', 'else')
        self.assertEqual(program_type, 'something')

        program_type = get_program_type('Agency FNMA Jumbo', 'FNMA')
        self.assertEqual(program_type, 'Jumbo')

        program_type = get_program_type('', 'invalid')
        self.assertEqual(program_type, 'unknown')
