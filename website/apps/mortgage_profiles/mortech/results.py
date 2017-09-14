from abc import ABCMeta
import logging
from decimal import Decimal

from core.utils import memoize
from mortgage_profiles.models import MortgageProfile
from mortgage_profiles.serializers import RateQuoteLenderSerializer
from mortgage_profiles.models import RateQuoteLender
from mortgage_profiles.mortech.calculations import MortechCalculations

logger = logging.getLogger('sample.mortech.results')


class MortechScenario(object):
    '''
    Abstract class for Mortech rate quote scenarios.

    Best Offer Strategy (BOS) returns a set of products defined by the Lender. These are preset
    loan offer configurations using up to 5 products for the selected loan package.

    TODO:
    * Loan Products/BOS search
    * Term
    * Amortization types
    * ltv, cltv
    * View (number of investors to display per rate)

    '''

    __metaclass__ = ABCMeta

    # TODO: Verify placement and values.
    LTV_LIMIT_FHA = 0.95
    LTV_LIMIT_VA = 0.80
    LOAN_AMOUNT_LIMIT_FHA = 625500
    LOAN_AMOUNT_LIMIT_CONFORMING = 417000
    LOAN_AMOUNT_LIMIT_CONFORMING_JUMBO = 625000

    # Type
    AMORTIZATION_TYPE_FIXED = 'Fixed'
    AMORTIZATION_TYPE_ARM = 'Variable'
    AMORTIZATION_TYPE_BALLOON = 'Balloon'
    AMORTIZATION_TYPE_OPTION_ARM = 'Option Arm'
    AMORTIZATION_TYPE_VARIABLE = 'Variable'

    # TERM IN YEARS
    AMORTIZATION_5 = '5 Year'
    AMORTIZATION_7 = '7 Year'
    AMORTIZATION_10 = '10 Year'
    AMORTIZATION_15 = '15 Year'
    AMORTIZATION_20 = '20 Year'
    AMORTIZATION_25 = '25 Year'
    AMORTIZATION_30 = '30 Year'
    AMORTIZATION_40 = '40 Year'

    SCENARIO_RECOMMENDATION = {
        MortgageProfile.LONG_TERM: (AMORTIZATION_30, AMORTIZATION_TYPE_FIXED),
        MortgageProfile.MEDIUM_TERM: (AMORTIZATION_30, AMORTIZATION_TYPE_FIXED),
        MortgageProfile.SHORT_TERM: (AMORTIZATION_7, AMORTIZATION_TYPE_ARM),
        MortgageProfile.NOT_SURE: (AMORTIZATION_30, AMORTIZATION_TYPE_FIXED),
    }

    def __init__(self, mortgage_profile):
        self.instance = mortgage_profile
        self.calculations = MortechCalculations

    @memoize
    def is_valid(self):
        """
        Return bool. Validation that results can be calculated.

        """
        logger.info('MORTECH-SCENARIO: EXISTS %s, LENDERS %s',
                    self.instance.rate_quote_requests.exists(),
                    self.instance.rate_quote_requests.first().rate_quote_lenders.exists())
        return (
            self.instance.rate_quote_requests.exists() and
            self.instance.rate_quote_requests.first().rate_quote_lenders.exists() and
            self.instance.ownership_time
        )

    def get_optimal_term_and_amortization_type(self):
        """
        Return optimal term and amortizaion_type based on profile data.

        """
        assert self.instance.ownership_time, "ownership_time missing value."
        logger.info('SCENARIO-RECOMMENDATION: %s', self.instance.ownership_time)

        return self.SCENARIO_RECOMMENDATION[self.instance.ownership_time]

    def get_fallback_term_and_amortization_type(self):
        return (self.AMORTIZATION_30, self.AMORTIZATION_TYPE_FIXED)

    def calculate(self, term=None, amortization_type=None, rate=None):
        """
        Return RateQuote lenders queryset that suits provided term and amortization_type.

        """
        lggr = logger.debug
        mtreq = self.instance.rate_quote_requests.first()
        queryset = mtreq.rate_quote_lenders.filter(
            term=term,
            amortization_type=amortization_type)
        if rate:
            # query for specific rate with minimal points
            queryset = queryset.filter(rate=rate).order_by('points')
            lggr('RESULTS-CALCULATE-RATE req %s term %s amrt %s rate %s count %s',
                 mtreq.id, term, amortization_type, rate, queryset.count())
            result = queryset.first()
        else:
            # query for lowest rate of top 5 products with credit closest to PAR
            qs = queryset.filter(points__lte=0.0).order_by('-points', 'rate')
            lggr('RESULTS-CALCULATE-POINTS req %s term %s amrt %s count %s',
                 mtreq.id, term, amortization_type, qs.count())
            if qs.exists():
                qs = qs[:5]
                result = min(qs, key=lambda item: item.rate)
            else:
                # adjust filter by increasing points threshold on original queryset
                lggr("RESULTS-CALCULATE-ADJUST-FILTER")
                result = self.adjust_filter(queryset)
        if result:
            lggr('RESULTS-CALCULATE-FOUND %s type %s rate %s points %s',
                 mtreq.id, result.program_type, result.rate, result.points)
        else:
            logger.info('RESULTS-CALCULATE-NOT-FOUND %s', mtreq.id)
        return result

    def adjust_filter(self, queryset):
        """Increase filter threshold by points and validate."""
        new_queryset = queryset.filter(points__gt=0.0).order_by('-points', 'rate')
        return self.validate_queryset(new_queryset)

    @classmethod
    def validate_queryset(cls, queryset):
        """Queryset should contain a valid lender."""
        if queryset:
            queryset = queryset[:5]
            result = min(queryset, key=lambda item: item.rate)
            return result
        else:
            return None

    @memoize
    def get_provided_loans(self):
        """
        Return possible RateQuote lender types.

        """
        assert self.is_valid(), "MortechScenario is invalid."

        return list(self.instance.rate_quote_requests.first().rate_quote_lenders.values(
            'amortization_type', 'term').order_by('-amortization_type', 'term'))

    def is_va_suitable(self, queryset):
        va_program_type = RateQuoteLender.PROGRAM_TYPE_CHOICES.va
        return (
            self.instance.is_veteran and
            queryset.filter(program_type=va_program_type).exists())

    @staticmethod
    def is_fha_suitable(queryset):
        fha_program_type = RateQuoteLender.PROGRAM_TYPE_CHOICES.fha
        return queryset.filter(program_type=fha_program_type).exists()

    @staticmethod
    def is_conf_suitable(queryset):
        conf_program_types = RateQuoteLender.PROGRAM_TYPE_CHOICES[
            RateQuoteLender.PROGRAM_TYPE_CHOICES.conforming]
        return queryset.filter(program_type__in=conf_program_types).exists()

    @staticmethod
    def is_conf_jumbo_suitable(queryset):
        conf_program_types = RateQuoteLender.PROGRAM_TYPE_CHOICES[
            RateQuoteLender.PROGRAM_TYPE_CHOICES.conforming]
        jumbo_string = RateQuoteLender.PROGRAM_TYPE_CHOICES.jumbo
        return queryset.filter(
            program_type__in=conf_program_types,
            program_name__contains=jumbo_string).exists()


class MortechScenarioPurchase(MortechScenario):
    """
    Scenario calculations for purchase mortgage profiles.

    """
    pass


class MortechScenarioRefinance(MortechScenario):
    """
    Scenario calculations for refinance mortgage profiles.

    """
    pass


class MortechDirector(object):
    """
    Object responsible for creation correct results instance depending on mortgage profile kind.

    """
    SCENARIO_KINDS = {
        MortgageProfile.PURCHASE: MortechScenarioPurchase,
        MortgageProfile.REFINANCE: MortechScenarioRefinance,
    }

    def __init__(self, mortgage_profile):
        self.instance = mortgage_profile

        mortech_scenario_class = self.SCENARIO_KINDS[self.instance.kind]
        self.scenario = mortech_scenario_class(self.instance)

    def is_valid(self):
        """
        Return bool. Validation that represent if results could be calculated.

        """
        return self.scenario.is_valid()

    def get_scenario(self, term=None, amortization_type=None):
        """
        Return mortech scenario results queryset depending on mortgage profile kind.

        """
        selected_term_and_type = (term is None) or (amortization_type is None)
        if selected_term_and_type:
            term, amortization_type = self.scenario.get_optimal_term_and_amortization_type()

        logger.debug('GET-SCENARIO: Term %s, Am %s', term, amortization_type)

        par_lender = self.scenario.calculate(term, amortization_type)
        if not par_lender and selected_term_and_type and (term == self.scenario.AMORTIZATION_7):
            logger.info('MOVING-TO-30-FIXED term %s type %s', term, amortization_type)
            term, amortization_type = self.scenario.get_fallback_term_and_amortization_type()
            par_lender = self.scenario.calculate(term, amortization_type)
        else:
            logger.debug('STAYING-WITH term %s type %s', term, amortization_type)

        lender = (self.scenario.calculate(term, amortization_type, rate=par_lender.rate)
                  if par_lender
                  else None)

        result = {
            'term': term,
            'amortization_type': amortization_type,
            'request_uuid': lender.request.uuid if lender else None,
            'results': RateQuoteLenderSerializer(lender).data if lender else None,
            'initial_data': getattr(self.instance, 'initial_data', None)
        }

        return result

    def get_full_scenario(self, term, amortization_type):
        """
        Provide quotes in a +/- 0.25% spread around the par rate
        """
        par_lender = self.scenario.calculate(term, amortization_type)
        if par_lender:
            lenders = []
            for difference in ['25.0', '12.5', '0.0', '-12.5', '-25.0']:
                rate = par_lender.rate + Decimal(difference)
                current = self.scenario.calculate(term, amortization_type, rate=rate)
                if current:
                    lenders.append(current)
        else:
            lenders = None

        scenario = {
            'term': term,
            'amortization_type': amortization_type,
            'results': RateQuoteLenderSerializer(lenders, many=True).data if lenders else None
        }
        return scenario

    # pylint: disable=no-self-use
    def get_errors(self):
        status = {
            'request exists': self.instance.rate_quote_requests.exists(),
            'lender exists': self.instance.rate_quote_requests.first().rate_quote_lenders.exists(),
            'ownership time': bool(self.instance.ownership_time)
        }

        errors = {'errors': dict((k, v) for k, v in status.items() if v is False)}
        return errors
