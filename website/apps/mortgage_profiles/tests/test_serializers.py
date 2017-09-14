from django.test import TestCase

from rest_framework.exceptions import ValidationError

from mortgage_profiles.models import MortgageProfile
from mortgage_profiles.factories import MortgageProfilePurchaseFactory, MortgageProfileRefinanceFactory
from mortgage_profiles.serializers import MortgageProfileSerializer, MortgageProfilePurchaseSerializer


class TestMortgageProfilePurchaseSerializer(TestCase):
    def test_basic(self):
        serializer = MortgageProfilePurchaseSerializer(data={
            'kind': MortgageProfile.PURCHASE,
            'purchase_timing': 'researching_options',
            'property_occupation': 'first_time_homebuyer',
            'property_type': 'single_family'
        })
        self.assertTrue(serializer.is_valid(raise_exception=True))


class TestMortgageProfileSerializer(TestCase):
    def test_purchase(self):
        mp = MortgageProfilePurchaseFactory(target_value=1000000)
        serializer = MortgageProfileSerializer(mp)
        self.assertEqual(serializer.data['target_value'], 1000000)
        self.assertEqual(serializer.data['kind'], 'purchase')

    def test_refinance(self):
        mp = MortgageProfileRefinanceFactory(mortgage_owe=1000000)
        serializer = MortgageProfileSerializer(mp)
        self.assertEqual(serializer.data['mortgage_owe'], 1000000)
        self.assertEqual(serializer.data['kind'], 'refinance')

    def test_invalid_instance_raises_error(self):
        mp = MortgageProfile()
        serializer = MortgageProfileSerializer(mp)
        with self.assertRaises(ValidationError):
            # pylint: disable=pointless-statement
            serializer.data
