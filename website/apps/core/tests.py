# -*- coding: utf-8 -*-
from collections import OrderedDict
import logging
import pytest

from django.utils.six import StringIO
from django.test import TestCase, override_settings
from django.conf import settings
from django.core.management import call_command

from rest_framework import serializers

from accounts.factories import CustomerFactory
from accounts.models import Advisor
from core import utils as core_utils
from core.models import Recaptcha, ResetToken
from core.parsers import camel_to_underscore, underscoreize, CamelCaseFormParser
from core.renderers import underscore_to_camelcase, camelize
from core.fields import MaskedField, SsnDashedField, SsnDigitsField
from pages.models import StateLicense

logger = logging.getLogger('sample.tests.smoke')


class CoreUtilsTest(TestCase):
    @override_settings(CP_URL={'PROTOCOL': 'https', 'HOST': 'example.com'})
    def test_get_consumer_portal_base_url_prod(self):
        expected_url = 'https://example.com'
        customer_portal_base_url = core_utils.get_consumer_portal_base_url()
        self.assertEqual(customer_portal_base_url, expected_url)


class CeleryTaskTestCase(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.BROKER_BACKEND = 'memory'
        super(CeleryTaskTestCase, self).setUp()


class UnderscoreToCamelcaseTestCase(TestCase):
    def test_default_cases(self):
        value_expected = (
            ('aaa_bbb_ccc', 'aaaBbbCcc'),
            ('_aaa_bbb_ccc', 'aaaBbbCcc'),
            ('aaa_bbb_ccc_', 'aaaBbbCcc'),
            ('AAA_BBB_CCC', 'aaaBbbCcc'),
            ('aaA_bbB_ccC', 'aaaBbbCcc'),
            ('1aa_2bb_3cc', '1aa2bb3cc'),
            ('aa1_bb2_cc3', 'aa1Bb2Cc3'),
            ('aaabbbccc', 'aaabbbccc'))
        for value, expected in value_expected:
            fn_value = underscore_to_camelcase(value)
            message = "'{}' => '{}' does not equal '{}'".format(value, fn_value, expected)
            self.assertEqual(fn_value, expected, msg=message)

    def test_capitalize_first_cases(self):
        value_expected = (
            ('aaa_bbb_ccc', 'AaaBbbCcc'),
            ('_aaa_bbb_ccc', 'AaaBbbCcc'),
            ('aaa_bbb_ccc_', 'AaaBbbCcc'),
            ('AAA_BBB_CCC', 'AaaBbbCcc'),
            ('aaA_bbB_ccC', 'AaaBbbCcc'),
            ('1aa_2bb_3cc', '1aa2bb3cc'),
            ('aa1_bb2_cc3', 'Aa1Bb2Cc3'),
            ('aaabbbccc', 'Aaabbbccc'))
        for value, expected in value_expected:
            fn_value = underscore_to_camelcase(value, lower_first=False)
            message = "'{}' => '{}' does not equal '{}'".format(value, fn_value, expected)
            self.assertEqual(fn_value, expected, msg=message)


class CamelizeTestCase(core_utils.FullDiffMixin, TestCase):
    def test_list_of_scalars(self):
        value = ['aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333]
        expected = ['aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333]
        self.assertEqual(camelize(value), expected)

    def test_tuple_of_scalars(self):
        value = ('aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333)
        expected = ('aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333)
        self.assertEqual(camelize(value), expected)

    def test_list_with_dicts(self):
        value = [
            {'aaa_bbb_ccc': 'aa_bb_cc'},
            {'ddd_eee_fff': 'dd_ee_ff', 'ggg_hhh_iii': 'gg_hh_ii'},
            {'jjj_kkk_lll': 'jj_kk_ll'},
            314, 271]
        expected = [
            {'aaaBbbCcc': 'aa_bb_cc'},
            {'dddEeeFff': 'dd_ee_ff', 'gggHhhIii': 'gg_hh_ii'},
            {'jjjKkkLll': 'jj_kk_ll'},
            314, 271]
        self.assertEqual(camelize(value), expected)

    def test_tuple_with_dicts(self):
        value = (
            {'aaa_bbb_ccc': 'aa_bb_cc'},
            {'ddd_eee_fff': 'dd_ee_ff', 'ggg_hhh_iii': 'gg_hh_ii'},
            {'jjj_kkk_lll': 'jj_kk_ll'},
            314, 271)
        expected = (
            {'aaaBbbCcc': 'aa_bb_cc'},
            {'dddEeeFff': 'dd_ee_ff', 'gggHhhIii': 'gg_hh_ii'},
            {'jjjKkkLll': 'jj_kk_ll'},
            314, 271)
        self.assertEqual(camelize(value), expected)

    def test_dict_of_things(self):
        value = {
            'aaa_bbb_ccc': 'aa_bb_cc',
            'ddd_eee_fff': ['dd_ee_ff', 111, {'ggg_hhh_iii': 'gg_hh_ii'}],
            'jjj_kkk_lll': 'jj_kk_ll',
            'mmm_nnn_ooo': ('mm_nn_oo', 222, {'ppp_qqq_rrr': 'pp_qq_rr'}),
            '314': 271}
        expected = {
            'aaaBbbCcc': 'aa_bb_cc',
            'dddEeeFff': ['dd_ee_ff', 111, {'gggHhhIii': 'gg_hh_ii'}],
            'jjjKkkLll': 'jj_kk_ll',
            'mmmNnnOoo': ('mm_nn_oo', 222, {'pppQqqRrr': 'pp_qq_rr'}),
            '314': 271}
        self.assertEqual(camelize(value), expected)

    def test_bad_keys(self):
        '''camelize() assumes all dictionary keys are strings'''
        values = ({314: 271},
                  {('aaa_bbb_ccc', 'ddd_eee_fff'): ('aa_bb_cc', 'dd_ee_ff')})
        for value in values:
            with self.assertRaises(AttributeError):
                camelize(value)

    def test_ordered_dict(self):
        '''ensure OrderedDicts are treated like dicts'''
        value = [OrderedDict([
            ('a_a', 1),
            ('b_b', 2),
            ('c_c', [
                OrderedDict([
                    ('pa_qb_rc', 25),
                    ('ax_by_cz', 26)])])])]
        expected = [
            {'aA': 1,
             'bB': 2,
             'cC': [{
                 'paQbRc': 25,
                 'axByCz': 26}]}]
        self.assertEqual(camelize(value), expected)


class CamelToUnderscoreTestCase(TestCase):
    def test_default_cases(self):
        value_expected = (
            ('aaaBbbCcc', 'aaa_bbb_ccc'),
            ('AaaBbbCcc', 'aaa_bbb_ccc'),
            ('aaaBbbCcc', 'aaa_bbb_ccc'),
            ('aaaBbbCcc', 'aaa_bbb_ccc'),
            ('1aa2bb3cc', '1aa2bb3cc'),
            ('1Aa2Bb3Cc', '1_aa2_bb3_cc'),
            ('aa1Bb2Cc3', 'aa1_bb2_cc3'),
            ('aaabbbccc', 'aaabbbccc'))
        for value, expected in value_expected:
            fn_value = camel_to_underscore(value)
            message = "'{}' => '{}' does not equal '{}'".format(value, fn_value, expected)
            self.assertEqual(fn_value, expected, msg=message)

    def test_dict_camelcase_to_underscore(self):
        """Should parse dictionary keys from camel to underscore."""
        parser = CamelCaseFormParser()
        data = 'kind=refinance&' \
               'propertyType=single_family&' \
               'propertyState=California&' \
               'propertyCity=San Francisco&' \
               'propertyZipcode=94111&' \
               'propertyCounty=San Francisco&' \
               'propertyValue=500000&' \
               'ownershipTime=long_term&' \
               'isVeteran=false&' \
               'referralUrl=http://localhost:8000&' \
               'conversionUrl=http://localhost:8000&' \
               'propertyOccupation=0&' \
               'creditScore=760&' \
               'ratePreference=fixed&' \
               'purpose=lower_mortgage_payments&' \
               'mortgageOwe=250000&' \
               'mortgageTerm=30_year&' \
               'mortgageMonthly_payment=1000&' \
               'cashout_amount=10000'
        expected = {
            u'kind': u'refinance',
            u'property_type': u'single_family',
            u'property_state': u'California',
            u'property_city': u'San Francisco',
            u'property_zipcode': u'94111',
            u'property_county': u'San Francisco',
            u'property_value': u'500000',
            u'ownership_time': u'long_term',
            u'is_veteran': u'false',
            u'referral_url': u'http://localhost:8000',
            u'conversion_url': u'http://localhost:8000',
            u'property_occupation': u'0',
            u'credit_score': u'760',
            u'rate_preference': u'fixed',
            u'purpose': u'lower_mortgage_payments',
            u'mortgage_owe': u'250000',
            u'mortgage_term': u'30_year',
            u'mortgage_monthly_payment': u'1000',
            u'cashout_amount': u'10000'
        }
        stream = StringIO(data)
        response = parser.parse(stream)
        msg = "{0} does not = {1}".format(response, expected)
        self.assertEqual(response, expected, msg)


class UnderscoreizeTestCase(TestCase):
    def test_list_of_scalars(self):
        value = ['aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333]
        expected = ['aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333]
        self.assertEqual(underscoreize(value), expected)

    def test_tuple_of_scalars(self):
        value = ('aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333)
        expected = ['aaa_bbb_ccc', 'ddd_eee_fff', 'ggg_hhh_iii', 111, 222, 333]
        self.assertEqual(underscoreize(value), expected)

    def test_list_with_dicts(self):
        value = [
            {'aaaBbbCcc': 'aa_bb_cc'},
            {'dddEeeFff': 'dd_ee_ff', 'gggHhhIii': 'gg_hh_ii'},
            {'jjjKkkLll': 'jj_kk_ll'},
            314, 271]
        expected = [
            {'aaa_bbb_ccc': 'aa_bb_cc'},
            {'ddd_eee_fff': 'dd_ee_ff', 'ggg_hhh_iii': 'gg_hh_ii'},
            {'jjj_kkk_lll': 'jj_kk_ll'},
            314, 271]
        self.assertEqual(underscoreize(value), expected)

    def test_tuple_with_dicts(self):
        value = (
            {'aaaBbbCcc': 'aa_bb_cc'},
            {'dddEeeFff': 'dd_ee_ff', 'gggHhhIii': 'gg_hh_ii'},
            {'jjjKkkLll': 'jj_kk_ll'},
            314, 271)
        expected = [
            {'aaa_bbb_ccc': 'aa_bb_cc'},
            {'ddd_eee_fff': 'dd_ee_ff', 'ggg_hhh_iii': 'gg_hh_ii'},
            {'jjj_kkk_lll': 'jj_kk_ll'},
            314, 271]
        self.assertEqual(underscoreize(value), expected)

    def test_dict_of_things(self):
        value = {
            'aaaBbbCcc': 'aa_bb_cc',
            'dddEeeFff': ['dd_ee_ff', 111, {'gggHhhIii': 'gg_hh_ii'}],
            'jjjKkkLll': 'jj_kk_ll',
            'mmmNnnOoo': ('mm_nn_oo', 222, {'pppQqqRrr': 'pp_qq_rr'}),
            '314': 271}
        expected = {
            'aaa_bbb_ccc': 'aa_bb_cc',
            'ddd_eee_fff': ['dd_ee_ff', 111, {'ggg_hhh_iii': 'gg_hh_ii'}],
            'jjj_kkk_lll': 'jj_kk_ll',
            'mmm_nnn_ooo': ['mm_nn_oo', 222, {'ppp_qqq_rrr': 'pp_qq_rr'}],
            '314': 271}
        self.assertEqual(underscoreize(value), expected)

    def test_bad_keys(self):
        '''underscoreize() assumes all dictionary keys are strings'''
        values = ({314: 271},
                  {('aaaBbbCcc', 'ddd_eee_fff'): ('aaBbCc', 'dd_ee_ff')})
        for value in values:
            with self.assertRaises(TypeError):
                underscoreize(value)


@pytest.mark.django_db
class DatabaseTestMixin(object):
    pytestmark = pytest.mark.django_db


class SsnDashedFieldTest(TestCase):
    def test_valid_outputs(self):
        valid_values = {
            '123-45-6789': u'123-45-6789',
            '': u''}
        field = SsnDashedField()
        for value, result in valid_values.items():
            self.assertEqual(field.to_internal_value(value), result)

    def test_invalid_values(self):
        field = SsnDashedField()
        invalid_values = (
            '12345678',
            '123456789',
            '123-45-678',
            '12-345-6789',
            '123-456-789',
            '1234-56-789',
            'ABCDEFGHI',
            'ABC-DE-FGHI')
        for value in invalid_values:
            with self.assertRaises(serializers.ValidationError) as cm:
                field.to_internal_value(value)
            self.assertEqual(str(cm.exception),
                             "[u'Incorrect format. Expected `XXX-XX-XXXX`.']")

    def test_representation(self):
        valid_results = {
            '123-45-6789': u'***-**-6789',
            '': u''}
        field = SsnDashedField()
        for value, result in valid_results.items():
            self.assertEqual(field.to_representation(value), result)


class SsnDigitsFieldTest(TestCase):
    def test_valid_outputs(self):
        valid_values = {
            '123456789': u'123-45-6789',
            '': u''}
        field = SsnDigitsField()
        for value, result in valid_values.items():
            self.assertEqual(field.to_internal_value(value), result)

    def test_invalid_values(self):
        field = SsnDigitsField()
        invalid_values = (
            '12345678',
            '1234567890',
            'ABCDEFGHI',
            '123-45-6789')
        for value in invalid_values:
            with self.assertRaises(serializers.ValidationError) as cm:
                field.to_internal_value(value)
            self.assertEqual(str(cm.exception),
                             "[u'Incorrect format. Expected `XXXXXXXXX`.']")

    def test_representation(self):
        valid_results = {
            '123-45-6789': u'*****6789',
            '': u''}
        field = SsnDigitsField()
        for value, result in valid_results.items():
            self.assertEqual(field.to_representation(value), result)


class MaskedFieldTest(TestCase):
    def test_representation(self):
        valid_values = {
            '': '',
            True: True,
            '12345': u'• • • 45',
            '123456789': u'• • • • • 6789'}
        field = MaskedField()
        for value, result in valid_values.items():
            self.assertEqual(field.to_representation(value), result)


class ResetTokenTests(TestCase):
    def test_manager_overrides(self):
        customer = CustomerFactory()
        with self.assertRaises(NotImplementedError):
            ResetToken.objects.create(customer=customer)
        with self.assertRaises(NotImplementedError):
            ResetToken.objects.get_or_create(customer=customer)
        with self.assertRaises(NotImplementedError):
            ResetToken.objects.update_or_create(customer=customer)
        with self.assertRaises(NotImplementedError):
            ResetToken.objects.get(customer=customer)

    def test_fetch_creates_new_token_if_none_exists(self):
        customer = CustomerFactory()
        self.assertFalse(ResetToken.objects.filter(customer=customer).exists())
        ResetToken.objects.fetch(customer)
        self.assertIsInstance(customer.reset_token, ResetToken)

    def test_fetch_returns_existing_token_if_one_exists(self):
        customer = CustomerFactory()
        reset_token = ResetToken(customer=customer)
        reset_token.save()
        fetched_token = ResetToken.objects.fetch(customer)
        self.assertEqual(reset_token.id, fetched_token.id)
        self.assertTrue(reset_token.updated < fetched_token.updated)

    def test_get_valid_token_returns_token(self):
        reset_token = ResetToken()
        reset_token.save()
        fetched_token = ResetToken.objects.get_valid_token(reset_token.token)
        self.assertEqual(reset_token.id, fetched_token.id)
        self.assertFalse(reset_token.updated < fetched_token.updated)

    def test_get_valid_token_does_not_return_expired_token(self):
        ResetToken.EXPIRATION_IN_HOURS = 0
        reset_token = ResetToken()
        reset_token.save()
        self.assertTrue(reset_token.has_expired)
        fetched_token = ResetToken.objects.get_valid_token(reset_token.token)
        self.assertIsNone(fetched_token)
        # the expired token is also deleted:
        self.assertFalse(ResetToken.objects.filter(id=reset_token.id).exists())
        # WARNING: must reset the expiration or else other tests will fail supriously
        ResetToken.EXPIRATION_IN_HOURS = 24


class StateUtilsTests(TestCase):
    STATES = {
        'ca': 'california',
        'CA': 'caLIFORNIA',
        'mD': 'MARYLAND',
        'tx': 'Texas',
    }

    def test_get_state_code(self):
        for code, name in self.STATES.items():
            self.assertEqual(core_utils.get_state_name(code), name.title())
            self.assertEqual(core_utils.get_state_name(name), name.title())

    def test_get_state_name(self):
        for code, name in self.STATES.items():
            self.assertEqual(core_utils.get_state_code(name), code.upper())
            self.assertEqual(core_utils.get_state_code(code), code.upper())

    def test_handle_none(self):
        self.assertIsNone(core_utils.get_state_name(None))
        self.assertIsNone(core_utils.get_state_code(None))


class IssampleEmailTests(TestCase):
    def test_checks_email(self):
        cases = {
            'jim@jim.com': False,
            'charles@anothersample.com': False,
            'jim@sample.com': True,
            '1': False,
            'some_random_string': False
        }
        for email, expected in cases.items():
            self.assertEqual(core_utils.is_sample_email(email), expected)


class IsUUIDTests(TestCase):
    def test_checks_uuid_correctly(self):
        checks = {
            'd9ae3337-229f-432a-aeba-dd498ebc64e4': True,
            'd9ae3337-229f-432a-aeba-dd498ebc64e4': True,
            'd9ae3337-229f-432a-aeba-dd498ebc64': False,
            'd9ae3337229f432aaebadd498ebc64e4': True,
            'hi': False,
            '12': False,
            12: False,
        }
        for uuid, result in checks.iteritems():
            self.assertEqual(core_utils.is_uuid4(uuid), result)


class ManagementCommandTests(TestCase):
    def test_update_license(self):
        """Should create or verify creation and storage 12 state licenses."""
        output = StringIO()
        expected = "Licenses updated.\n"
        call_command('update_licenses', stdout=output)
        states = StateLicense.objects.all()
        self.assertEqual(len(states), 12)
        self.assertEqual(expected, output.getvalue())

    def test_update_recaptcha(self):
        """Should create or verify creation of recaptcha credentials."""
        output = StringIO()
        expected = 'Recaptcha update complete!\n'
        call_command('update_recaptcha', stdout=output)
        recaptcha = Recaptcha.objects.all()
        self.assertEqual(len(recaptcha), 1)
        self.assertEqual(expected, output.getvalue())

    def test_add_groups(self):
        """Should create or verify creation of mortgage_advisors group."""
        output = StringIO()
        expected = 'Advisor user and mortgage_advisors group complete.'
        call_command('add_groups', stdout=output)
        advisor = Advisor.objects.get(email='advisor@example.com')
        self.assertTrue(advisor in Advisor.objects.filter(groups__name='mortgage_advisors'))
        # Two statements are returned by the command: verify the final one.
        self.assertEqual(expected, output.getvalue().split('\n')[1])
