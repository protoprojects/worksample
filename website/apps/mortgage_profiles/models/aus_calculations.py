from decimal import Decimal

from loans.models import HoldingAssetV1


# pylint: disable=too-many-instance-attributes
class AusCalculations(object):
    """
    these calculations are meant to equal those returned by AUS

    all calculations return a Decimal (except for reserve_months)
    """
    def __init__(self, rate_quote_lender):
        mortgage_profile = rate_quote_lender.mortgage_profile
        primary_borrower = rate_quote_lender.primary_borrower

        insurance_taxes_hoa = sum([rate_quote_lender.escrowed_insurance,
                                   rate_quote_lender.escrowed_taxes,
                                   (rate_quote_lender.mortgage_profile.hoa_dues or Decimal('0.00'))])
        # LoanDetails
        self.base_loan_amount = Decimal(mortgage_profile.get_loan_amount())
        self.ltv = Decimal(mortgage_profile.get_loan_to_value() * 100)
        self.property_estimated_value = Decimal(mortgage_profile.get_property_value())
        # Note Rate and Qualifying Rate
        self.note_rate = Decimal(rate_quote_lender.rate / 100)
        self.note_principal_and_interest = Decimal(rate_quote_lender.monthly_payment)
        self.note_total_housing_payment = self.note_principal_and_interest + insurance_taxes_hoa
        self.qualifying_rate = rate_quote_lender.qualifying_rate
        self.qualifying_principal_and_interest = self.get_pi(self.qualifying_rate, self.base_loan_amount)
        self.qualifying_total_housing_payment = self.qualifying_principal_and_interest + insurance_taxes_hoa
        # Underwriting Analysis
        self.cash_back = self._cash_back(mortgage_profile)
        self.available_funds = self._available_funds(primary_borrower)
        self.required_funds = self._required_funds(mortgage_profile)
        _reserves = self.available_funds - self.required_funds
        self.reserves = max(_reserves, Decimal('0.00'))
        self.shortage = abs(min(_reserves, Decimal('0.00')))
        self.reserve_months = round(self.reserves / self.qualifying_total_housing_payment, 2)

    @staticmethod
    def _available_funds(primary_borrower):
        funds = Decimal('0.00')
        assets = primary_borrower.holding_assets.filter(kind=HoldingAssetV1.OTHER_LIQUID_ASSETS)
        if assets.exists():
            funds = assets.first().current_value
        return funds

    @staticmethod
    def _cash_back(mortgage_profile):
        return (mortgage_profile.cashout_amont
                if mortgage_profile.kind == mortgage_profile.REFINANCE
                else Decimal('0.00'))

    @staticmethod
    def _required_funds(mortgage_profile):
        # XXX:rex update to work for refi as well
        return Decimal(mortgage_profile.purchase_down_payment)

    @staticmethod
    def get_pi(rate, loan_amount):
        """
        rate is passed in as percentage points, ex: 4.00
        """
        # convert rate to ratio, ex: 4.00 => 0.04, then convert to a monthly rate
        monthly_rate = Decimal(rate) / Decimal('100') / 12
        return Decimal(loan_amount * ((monthly_rate * ((1 + monthly_rate) ** 360)) / ((1 + monthly_rate) ** 360 - 1)))

    @staticmethod
    def _total_income(primary_borrower, primary_coborrower):
        bor_income = sum([income.value for income in primary_borrower.income.all() if income.value])
        cob_income = (sum([income.value for income in primary_coborrower.income.all() if income.value])
                      if primary_coborrower else Decimal('0.00'))
        return bor_income + cob_income
