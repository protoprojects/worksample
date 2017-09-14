import factory as factory_boy
from factory import fuzzy

from core.utils import create_shortuuid

from mortgage_profiles.models import (
    RateQuoteLender,
    RateQuoteRequest,
    MortgageProfile,
    MortgageProfilePurchase,
    MortgageProfileRefinance,
)


class MortgageProfilePurchaseFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = MortgageProfilePurchase

    uuid = fuzzy.FuzzyAttribute(create_shortuuid)
    kind = MortgageProfilePurchase.PURCHASE
    credit_score = 850
    is_veteran = True
    purchase_timing = MortgageProfilePurchase.RESEARCHING_OPTIONS
    property_occupation = MortgageProfilePurchase.FIRST_TIME_HOMEBUYER
    purchase_down_payment = 400000
    target_value = 1000000
    property_county = 'Secret county'
    property_state = 'California'
    property_type = MortgageProfile.PROPERTY_TYPE_SINGLE_FAMILY
    ownership_time = MortgageProfile.SHORT_TERM


class MortgageProfileRefinanceFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = MortgageProfileRefinance

    uuid = fuzzy.FuzzyAttribute(create_shortuuid)
    kind = MortgageProfilePurchase.REFINANCE
    credit_score = fuzzy.FuzzyInteger(300, 850)
    is_veteran = fuzzy.FuzzyChoice([True, False])
    mortgage_owe = fuzzy.FuzzyInteger(15000, 105000)
    ownership_time = fuzzy.FuzzyChoice(dict(MortgageProfile.OWNERSHIP_TIME_CHOICES).keys())
    property_county = 'Secret county'
    property_occupation = fuzzy.FuzzyChoice(dict(MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES).keys())
    property_state = 'California'
    property_type = fuzzy.FuzzyChoice(dict(MortgageProfile.PROPERTY_TYPE_CHOICES).keys())
    property_value = fuzzy.FuzzyInteger(115000, 245000)


class RateQuoteRequestFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = RateQuoteRequest

    uuid = fuzzy.FuzzyAttribute(create_shortuuid)
    mortgage_profile = factory_boy.SubFactory(MortgageProfilePurchaseFactory)


class RateQuoteLenderFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = RateQuoteLender

    request = factory_boy.SubFactory(RateQuoteRequestFactory)

    term = '15 Year'
    amortization_type = 'Fixed'
    piti = 1200
    program_name = 'Test 15 Year Fixed'
    program_type = 'FHA'
    points = 0.0
    rate = 250.0
    monthly_premium = 400
    apr = 99.9
