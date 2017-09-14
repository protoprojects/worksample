# -*- coding: utf-8 -*-
import logging

from decimal import Decimal
from core.utils import memoize

from mortgage_profiles.mortech.api import MortechApi

logger = logging.getLogger("sample.mortech.fees")


class MortechFees(object):
    """
    Contains specific APR calculation based on Mortech lender information.
    Mortgage formulae reference: http://www.efunda.com/formulae/finance/apr_calculator.cfm
    """

    LTV_LIMIT = 0.8

    COST_OF_CHOSEN_RATE = 'cost_of_chosen_rate'
    TAX_SERVICE_FEE = 'tax_service_fee'
    UNDERWRITING = 'underwriting'
    FLOOD_CERTIFICATION = 'flood_certification'
    UPFRONT_MORTGAGE_INSURANCE_PREMIUM = 'upfront_mortgage_insurance_premium'
    FUNDING_FEE = 'funding_fee'
    PREPAID_INTEREST = 'initial_interest'  # We can no longer edit templates. This must stay. XXXkayhudson
    ESCROWED_INSURANCE = 'escrowed_insurance'
    ESCROWED_TAXES = 'escrowed_taxes'
    MORTGAGE_INSURANCE = 'mortgage_insurance'
    ESTIMATED_APPRAISAL_FEE = 'estimated_appraisal_fee'
    TITLE_FEE = 'title_fee'
    ESCROW_FEE = 'escrow_fee'
    CREDIT_REPORT_FEE = 'credit_report_fee'

    LENDER_TERM = {
        '3 Year': 3,
        '5 Year': 5,
        '7 Year': 7,
        '10 Year': 10,
        '15 Year': 15,
        '20 Year': 20,
        '25 Year': 25,
        '30 Year': 30,
        '40 Year': 40
    }

    def __init__(self, instance, lender):
        self.instance = instance
        self.calculations = MortechApi(instance).calculations
        self.lender = lender
        self.fees = self.get_fees()

    @memoize
    def get_escrowed_insurance(self):
        """
        Details: Loan amount * 0.00375 / 12

        """
        return Decimal(self.get_loan_amount()) * Decimal(0.00375 / 12)

    @memoize
    def get_escrowed_taxes(self):
        """
        Details: Property value * 0.0125 / 12

        """
        return Decimal(self.instance.get_property_value() * 0.0125 / 12)

    def get_fees(self):
        """
        Return dict that contains fee id as a key and fee value as a value.
        """
        return {
            self.UNDERWRITING: self.lender.underwriting_fee,
            self.FLOOD_CERTIFICATION: self.lender.flood_certification,
            self.UPFRONT_MORTGAGE_INSURANCE_PREMIUM: self.lender.upfront_fee,
            self.TAX_SERVICE_FEE: self.lender.tax_service_fee,
            self.ESCROWED_TAXES: self.get_escrowed_taxes(),
            self.ESCROWED_INSURANCE: self.get_escrowed_insurance(),
            self.PREPAID_INTEREST: self.get_prepaid_interest(),
            self.MORTGAGE_INSURANCE: self.get_mortgage_insurance(),
            self.COST_OF_CHOSEN_RATE: self.get_cost_of_chosen_rate(),
            self.ESTIMATED_APPRAISAL_FEE: self.lender.estimated_appraisal_fee,
            self.TITLE_FEE: self.lender.title_fee,
            self.ESCROW_FEE: self.lender.escrow_fee,
            self.CREDIT_REPORT_FEE: self.lender.credit_report_fee,
        }

    def get_non_zero_fees(self):
        """
        Provide all non-zero fees (COST_OF_CHOSEN_RATE is always returned).

        Avoids returning any fees which might be unknown and treated as zero.

        """
        fees = self.get_fees()
        return {fee: value for fee, value in fees.items()
                if ((fee == self.COST_OF_CHOSEN_RATE) or
                    not ((value is None) or Decimal(value).is_zero()))}

    @memoize
    def get_cost_of_chosen_rate(self):
        """
        Cost = Loan amount * lender.points
        """
        return self.get_loan_amount() * self.lender.points / 100

    @memoize
    def get_prepaid_interest(self):
        """
        Details: Initial Interest = Loan Amount * Interest Rate *
        (30 for 30 year fixed and the ARMs or 15 for 15 year Fixed)
        divided by Loan Term in months (360 for 30 yr fixed and ARMS, 180 for 15 year fixed)

        """
        rate = self.lender.rate / 100
        term = 365 * self.LENDER_TERM.get(self.lender.term)
        prepaid_interest = (self.lender.prepaid_interest
                            if self.lender.prepaid_interest
                            else self.get_loan_amount() * rate / term)

        return Decimal(prepaid_interest)

    @memoize
    def get_mortgage_insurance(self):
        """
        Return monthly mortgage fee.
        LTV and other adjustments are pre-calculated by Mortech.
        """
        result = 0 if self.lender.monthly_premium is None else self.lender.monthly_premium
        logger.debug(u"Mortgage insurance: %s, Lender: %s.", result, self.lender)
        return Decimal(result)

    @memoize
    def get_total_fees(self):
        """
        Return total fees for rate-quote results page.
        """
        fees = [
            self.lender.underwriting_fee,
            self.get_cost_of_chosen_rate(),
            self.lender.tax_service_fee,
            self.lender.upfront_fee,
            self.get_prepaid_interest(),
            self.lender.estimated_appraisal_fee,
            self.lender.title_fee,
            self.lender.escrow_fee,
            self.lender.credit_report_fee]
        result = sum([Decimal(fee) for fee in fees
                      if not ((fee is None) or Decimal(fee).is_zero())])

        logger.debug(u"Total fees: %s, Lender: %s.", result, self.lender)
        return result

    @memoize
    def get_total_monthly_payment(self):
        '''Return total monthly payment, lender.piti will not include any taxes nor escrow fees.'''
        result = sum([
            self.lender.monthly_payment,
            self.get_escrowed_insurance(),
            self.get_escrowed_taxes(),
            self.get_mortgage_insurance()
        ])

        logger.debug(u"Total monthly payment: %s, Lender: %s.", result, self.lender)

        return result

    def get_loan_amount(self):
        return self.calculations.get_loan_amount()
