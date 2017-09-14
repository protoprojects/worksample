import logging
from abc import ABCMeta, abstractmethod

from django.conf import settings
from core.utils import memoize
from mortgage_profiles.models import (
    MortgageProfile, MortgageProfilePurchase,
    MortgageProfileRefinance)


logger = logging.getLogger("sample.mortech.calculations")


class MortechCalculations(object):
    """
    Parent object for Mortech calculations using MortgageProfile data. Converts model data
    into parameters for the Mortech request.

    Constants hardcoded from Mortech API docs.

    Condos:
    Warrantable (default): condos which meet Fannie Mae and Freddie Mac mortgage standards.
    Unwarrantable: do not meet those standards. Common examples: condotels and time shares.
    Source: http://themortgagereports.com/18658/condo-mortgage-non-warrantable-loan-rates-gina-pogol
    """
    __metaclass__ = ABCMeta

    # Loan purposes
    LOAN_PURPOSE_PURCHASE = 0
    LOAN_PURPOSE_RATE_AND_TERM = 1  # Refi
    LOAN_PURPOSE_CASHOUT = 2        # Refi
    LOAN_PURPOSE_HOME_EQUITY = 3    # Refi
    LOAN_PURPOSE_HELOC = 4          # Refi

    LOAN_PURPOSE_MAPPING = {
        MortgageProfileRefinance.CASH_OUT: LOAN_PURPOSE_CASHOUT,
        MortgageProfileRefinance.LOWER_MORTGAGE_PAYMENTS: LOAN_PURPOSE_RATE_AND_TERM,
        MortgageProfileRefinance.BOTH: LOAN_PURPOSE_HOME_EQUITY,
        MortgageProfileRefinance.HELOC: LOAN_PURPOSE_HELOC
    }

    # Property types
    PROPERTY_TYPE_1_UNIT = 0
    PROPERTY_TYPE_2_UNIT = 1
    PROPERTY_TYPE_3_UNIT = 2
    PROPERTY_TYPE_4_UNIT = 3
    PROPERTY_TYPE_COOPS = 4
    PROPERTY_TYPE_MANUFACTURED_HOME = 5
    PROPERTY_TYPE_CONDOS_LOW = 6   # 1-4
    PROPERTY_TYPE_CONDOS_MID = 7   # 5-8
    PROPERTY_TYPE_CONDOS_HIGH = 8  # >8
    PROPERTY_TYPE_UNWARRANTED_CONDOS_LOW = 9
    PROPERTY_TYPE_UNWARRANTED_CONDOS_MID = 10
    PROPERTY_TYPE_UNWARRANTED_CONDOS_HIGH = 11
    PROPERTY_TYPE_CONDOTEL_LOW = 12
    PROPERTY_TYPE_CONDOTEL_MID = 13
    PROPERTY_TYPE_CONDOTEL_HIGH = 14
    PROPERTY_TYPE_TOWNHOMES = 15
    PROPERTY_TYPE_DETACHED_CONDO = 20
    PROPERTY_TYPE_MAPPING = {
        MortgageProfile.PROPERTY_TYPE_SINGLE_FAMILY: PROPERTY_TYPE_1_UNIT,
        MortgageProfile.PROPERTY_TYPE_CONDO_LESS_5: PROPERTY_TYPE_CONDOS_LOW,
        MortgageProfile.PROPERTY_TYPE_CONDO__5_8: PROPERTY_TYPE_CONDOS_MID,
        MortgageProfile.PROPERTY_TYPE_CONDO_MORE_8: PROPERTY_TYPE_CONDOS_HIGH,
        MortgageProfile.PROPERTY_TYPE_TOWNHOUSE: PROPERTY_TYPE_TOWNHOMES,
        MortgageProfile.PROPERTY_TYPE_TWO_UNIT: PROPERTY_TYPE_2_UNIT,
        MortgageProfile.PROPERTY_TYPE_THREE_UNIT: PROPERTY_TYPE_3_UNIT,
        MortgageProfile.PROPERTY_TYPE_FOUR_UNIT: PROPERTY_TYPE_4_UNIT,
        MortgageProfile.PROPERTY_TYPE_MANUFACTURED_SINGLE: PROPERTY_TYPE_MANUFACTURED_HOME
    }

    OCCUPANCY_TYPE_OWNER_OCCUPIED = 0
    OCCUPANCY_TYPE_NON_OWNER_OCCUPIED = 1
    OCCUPANCY_TYPE_SECOND_HOME = 2

    PURCHASE_TYPE_MAPPING = {
        # Purchase
        MortgageProfilePurchase.FIRST_TIME_HOMEBUYER: OCCUPANCY_TYPE_OWNER_OCCUPIED,
        MortgageProfilePurchase.SELLING_HOME: OCCUPANCY_TYPE_OWNER_OCCUPIED,
        MortgageProfilePurchase.VACATION_HOME: OCCUPANCY_TYPE_SECOND_HOME,
        MortgageProfilePurchase.INVESTMENT_PROPERTY: OCCUPANCY_TYPE_NON_OWNER_OCCUPIED,
        # Refinance
        MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES.primary: OCCUPANCY_TYPE_OWNER_OCCUPIED,
        MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES.secondary: OCCUPANCY_TYPE_SECOND_HOME,
        MortgageProfileRefinance.PROPERTY_OCCUPATION_CHOICES.investment: OCCUPANCY_TYPE_NON_OWNER_OCCUPIED
    }

    def __init__(self, mortgage_profile):
        self.instance = mortgage_profile

    def is_enough_data(self):
        '''Return results only if all required fields are valid.'''
        result = all([getattr(self.instance, field, None) is not None for field in self.get_required_fields()])

        logger.debug(u"DATA-SUFFICIENT: %s for Profile: %s, User: %s.",
                     result, self.instance.get_kind_display(), self.instance.user)

        return result

    def is_valid_state(self):
        assert self.instance.property_state is not None, 'self.instance.property_state is None'
        logger.info('CALCULATION-IS-VALID-STATE state %s code %s',
                    self.instance.property_state,
                    self.instance.property_state_code)
        return self.instance.property_state in settings.STATE_NAMES

    def get_property_state_code(self):
        return self.instance.property_state_code

    def get_property_state(self):
        return self.instance.property_state

    def get_property_county(self):
        return self.instance.property_county

    @abstractmethod
    def get_required_fields(self):
        '''Return list of required field names for calculations.'''
        return [
            'credit_score',
            'property_state'
        ]

    @memoize
    def get_loan_amount(self):
        """
        Return loan amount.

        """
        return self.instance.get_loan_amount()

    @memoize
    def get_property_value(self):
        """
        Return property value.

        """
        return self.instance.get_property_value()

    # pylint: disable=no-self-use
    def get_cashout_amount(self):
        """
        Return cashout amount. `None` by default. Overridden in children.

        """
        return

    @abstractmethod
    def get_loan_purpose(self):
        """
        Abstract method. Return loan purpose. Overridden in children.

        """
        pass

    @abstractmethod
    def get_property_type(self):
        """
        Abstract method. Return property type. Overridden in children.

        """
        pass

    @abstractmethod
    def get_occupancy_type(self):
        """Return occupancy type."""
        pass

    def get_military(self):
        """Return military status."""
        return self.instance.is_veteran or False

    @memoize
    def get_loan_to_value(self):
        """Return LTV ratio."""
        return self.instance.get_loan_to_value()

    def get_county(self):
        """Return property county."""
        return self.instance.property_county_name

    def get_zipcode(self):
        """Return property zipcode."""
        return self.instance.property_zipcode

    def is_condo(self):
        condo_types = (MortgageProfile.PROPERTY_TYPE_CONDO_LESS_5,
                       MortgageProfile.PROPERTY_TYPE_CONDO__5_8,
                       MortgageProfile.PROPERTY_TYPE_CONDO_MORE_8,
                       MortgageProfile.PROPERTY_TYPE_CONDOS_LIMITED,
                       MortgageProfile.PROPERTY_TYPE_CONDOS_UNAPPROVED,
                       MortgageProfile.PROPERTY_TYPE_CONDOTELS)
        return self.instance.property_type in condo_types


class MortechCalculationsPurchase(MortechCalculations):

    def get_required_fields(self):
        """Return list of required field names for purchase calculations."""
        fields = super(MortechCalculationsPurchase, self).get_required_fields()
        return fields + [
            'target_value',
            'purchase_down_payment',
        ]

    def get_loan_purpose(self):
        """Return loan purpose for purchase profiles."""
        result = self.LOAN_PURPOSE_PURCHASE

        logger.info(u"MORTECH-CALCULATIONS-PURCHASE type: %s for Profile: %s, User: %s.",
                    result, self.instance.get_kind_display(), self.instance.user)

        return result

    def get_property_type(self):
        """Return property type for purchase profiles."""
        assert self.instance.property_type, "property_type missing value."

        return self.PROPERTY_TYPE_MAPPING.get(self.instance.property_type)

    def get_occupancy_type(self):
        """Return occupancy type."""
        return self.PURCHASE_TYPE_MAPPING.get(self.instance.property_occupation)


class MortechCalculationsRefinance(MortechCalculations):

    def get_required_fields(self):
        """Return list of required field names for refinance calcualtions."""
        fields = super(MortechCalculationsRefinance, self).get_required_fields()
        return fields + [
            'property_type',
            'property_value',
            'mortgage_owe',
            'purpose'
        ]

    def get_loan_purpose(self):
        """Return loan purpose parameter for refinance profiles."""
        assert self.instance.purpose, "purpose missing value."

        logger.info(u"GET-PURPOSE-TYPE: %s for Profile: %s, User: %s.",
                    self.instance.purpose, self.instance.get_kind_display(), self.instance.user)
        return self.LOAN_PURPOSE_MAPPING[self.instance.purpose]

    def get_cashout_amount(self):
        """Return cashout amount for refinance profiles."""
        assert self.instance.purpose, "purpose missing value."

        if self.instance.purpose == MortgageProfileRefinance.CASH_OUT:
            result = self.instance.cashout_amount
        else:
            result = None

        logger.info(u"GET-CASHOUT-AMOUNT: %s for Profile: %s, User: %s",
                    result, self.instance.get_kind_display(), self.instance.user)

        return result

    def get_property_type(self):
        """Return property type for refinance profiles."""
        # TODO: This should be in get_required_fields if it is to be a required field.
        assert self.instance.property_type, "property_type missing value."

        logger.info(u"GET-PROPERTY-TYPE: %s for Profile: %s, User: %s",
                    self.instance.property_type, self.instance.get_kind_display(), self.instance.user)

        return self.PROPERTY_TYPE_MAPPING.get(self.instance.property_type)

    def get_occupancy_type(self):
        """Return occupancy type for refinance profiles."""
        # TODO: This should be in get_required_fields if it is to be a required field.
        assert self.instance.property_occupation, "property_occupation missing value."

        return self.PURCHASE_TYPE_MAPPING.get(self.instance.property_occupation)
