# -*- coding: utf-8 -*-

# pylint: disable=W0108
import datetime
import json
import string
import uuid

import factory
import factory.fuzzy

from django.utils.encoding import force_text

from accounts.factories import AdvisorFactory, CoordinatorFactory, CustomerFactory, RealtorFactory, SpecialistFactory

from loans.models import (
    AddressV1, BorrowerV1, CoborrowerV1, ContactV1, DemographicsV1, EmploymentV1,
    LoanV1, LoanProfileV1, sampleTeamV1,
    HoldingAssetV1, InsuranceAssetV1, VehicleAssetV1,
    IncomeV1, ExpenseV1, LiabilityV1,
)


START_DATE_BEGIN = 5
START_DATE_END = 3

YEARS_IN_FIELD_MIN = 2
YEARS_IN_FIELD_MAX = 20

# Days from now
LOCK_DATE_MIN = 1
LOCK_DATE_MAX = 30

LOCK_DAYS_MIN = 3
LOCK_DAYS_MAX = 21

LOAN_TARGET_CLOSE_DATE_OFFSET = 14

# Principal Residence, Second Home, Investment Property
PREVIOUS_PROPERTY_TYPE_CHOICES = {
    'principal_residence': 'PrimaryResidence',
    'second_home': 'SecondaryResidence',
    'investment_property': 'Investment'}

# Sole, Jointly w/Spouse, Jointly w/Other
PREVIOUS_PROPERTY_TITLE_HELD_CHOICES = {
    'sole': 'Sole',
    'joint_with_spouse': 'JointWithSpouse',
    'jointly_other': 'JointWithOther'}

STATES = ('CA', 'CO', 'DC', 'WA')

FIRST_NAME_CHOICES = (u'Alex', u'Alina', u'Anastasia', u'Anna', u'Anton',
                      u'Artem', u'Chloe', u'Daniel', u'Dasha', u'Denis',
                      u'Dima', u'Elizabeth', u'Emily', u'Emma', u'Harry',
                      u'Igor', u'Jack', u'James', u'Jessica', u'Joseph',
                      u'Joshua', u'Julia', u'Kate', u'Lauren', u'Maria',
                      u'Marina', u'Matthew', u'Megan', u'Nastya', u'Nazar',
                      u'Olivia', u'Samuel', u'Sarah', u'Sasha', u'Sophie',
                      u'Thomas', u'Vadim', u'Victoria', u'Vova', u'William')

MIDDLE_NAME_CHOICES = (u'Achilles', u'Adonis', u'Aeneas', u'Agatha', u'Alexa',
                       u'Alexandre', u'Althea', u'Amara', u'Ambrose', u'Anastasia',
                       u'Apollonia', u'Ariane', u'Athena', u'Calista', u'Cassia',
                       u'Damien', u'Dimitri', u'Dorian', u'Galen', u'Giles')

LAST_NAME_CHOICES = (u'Flores', u'García', u'González', u'Heikkinen', u'Hernández',
                     u'Hämäläinen', u'Järvinen', u'Korhonen', u'Koskinen', u'Laine',
                     u'López', u'Martínez', u'Mäkelä', u'Mäkinen', u'Nieminen',
                     u'Pérez', u'Ramírez', u'Rivera', u'Rodríguez', u'Virtanen')


BORROWER_AGE_MIN = 22
BORROWER_AGE_MAX = 90


PURPOSE_OF_REFINANCE_CHOICES = (
    'cash_out_debt_consolidation'
    'cash_out_home_improvement',
    'cash_out_other',
    'rate_or_term',
    'fha_streamlined',
    'va_irrrl')

PROPERTY_TYPE_CHOICES = (
    'single_family_residence',
    'condo_townhome',
    'high_rise_condominium',
    'manufactured_housing',
    'pud',
    '2_4_unit',
    'coop',
    'mixed_use')


ETHNICITY_CHOICES = (
    u'hispanic_or_latino',
    u'not hispanic_or_latino',
    u'information_not_provided',
    u'not_applicable')


GENDER_CHOICES = (
    u'female',
    u'male',)


GENDER_CHOICES_UNUSED = (
    u'not_provided',
    u'not_applicable')


HOW_TITLE_HELD_CHOICES = ('community_property',
                          'joint_tenants',
                          'single_man',
                          'single_woman',
                          'married_man',
                          'married_woman',
                          'tenancy_in_common',
                          'tenancy_by_entirety',
                          'to_be_decided_in_escrow',
                          'unmarried_man',
                          'unmarried_woman',
                          'other')


HOW_ESTATE_HELD_CHOICES = (
    'fee_simple',
    'leasehold')


def many_to_many_create_hook(obj, attr, create, extracted, **kwargs):
    """
    Generic Many-to-Many post-generation hook
    """
    if create:
        if extracted:
            for item in extracted:
                getattr(obj, attr).add(item)


class FuzzyAgeDate(factory.fuzzy.FuzzyDate):
    """
    Generate a date some number of years in the past
     """
    DAYS_PER_YEAR = 365.25

    def __init__(self, age_min, age_max):
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=(age_max * self.DAYS_PER_YEAR))
        end_date = today - datetime.timedelta(days=(age_min * self.DAYS_PER_YEAR))
        super(FuzzyAgeDate, self).__init__(start_date, end_date)


class FuzzyBoolean(factory.fuzzy.FuzzyChoice):
    """
    Generate a boolean
    """
    def __init__(self):
        super(FuzzyBoolean, self).__init__([False, True])


class FuzzyFutureDate(factory.fuzzy.FuzzyDate):
    """Generate a date in the future"""
    def __init__(self, start_days_from_now, end_days_from_now=None):
        today = datetime.date.today()
        if end_days_from_now is None:
            start_date = today
            end_date = today + datetime.timedelta(start_days_from_now)
        else:
            start_date = today + datetime.timedelta(start_days_from_now)
            end_date = today + datetime.timedelta(end_days_from_now)
        super(FuzzyFutureDate, self).__init__(start_date, end_date)


class FuzzyPastDate(factory.fuzzy.FuzzyDate):
    """Generate a date in the past"""
    def __init__(self, end_days_from_now, start_days_from_now=None):
        today = datetime.date.today()
        if start_days_from_now is None:
            end_date = today
            start_date = today - datetime.timedelta(end_days_from_now)
        else:
            end_date = today - datetime.timedelta(end_days_from_now)
            start_date = today - datetime.timedelta(start_days_from_now)
        super(FuzzyPastDate, self).__init__(start_date, end_date)


class FuzzyPrefixedFloat(factory.fuzzy.BaseFuzzyAttribute):
    def __init__(self, prefix):
        self.prefix = prefix

    def fuzz(self):
        # pylint: disable=W0212
        rnd = factory.fuzzy._random
        return '{}{}'.format(self.prefix, rnd.random())


class FuzzyZipCode(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        # pylint: disable=W0212
        rnd = factory.fuzzy._random
        return '{0:05d}'.format(rnd.randrange(100000))


class FuzzyArraySample(factory.fuzzy.BaseFuzzyAttribute):
    '''Provide a random-sized, random sample of a population'''
    def __init__(self, population):
        self.population = population
        super(FuzzyArraySample, self).__init__()

    def fuzz(self):
        # pylint: disable=W0212
        rnd = factory.fuzzy._random
        k = rnd.randint(0, len(self.population))
        k = min(k, len(self.population))
        return rnd.sample(self.population, k)


class FuzzyPhoneNumber(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        # pylint: disable=W0212
        rnd = factory.fuzzy._random
        return '{0}{1:02d}-{2}{3:02d}-{4:04d}'.format(rnd.randrange(10),
                                                      rnd.randrange(100),
                                                      rnd.randrange(10),
                                                      rnd.randrange(100),
                                                      rnd.randrange(10000))


class FuzzySsn(factory.fuzzy.BaseFuzzyAttribute):
    def __init__(self, sep='-'):
        self.sep = sep
        super(FuzzySsn, self).__init__()

    def fuzz(self):
        # pylint: disable=W0212
        rnd = factory.fuzzy._random
        return '{0:03d}{3}{1:02d}{3}{2:04d}'.format(rnd.randrange(1000),
                                                    rnd.randrange(100),
                                                    rnd.randrange(10000),
                                                    self.sep)


class AddressV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = AddressV1

    street = factory.fuzzy.FuzzyText(length=3, chars=string.digits, suffix=' Main St')
    city = 'Springfield'
    state = factory.fuzzy.FuzzyChoice(STATES)
    postal_code = FuzzyZipCode()
    end_date = datetime.date.today()
    start_date = factory.fuzzy.FuzzyDate(datetime.date(2000, 5, 1))


class ContactV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = ContactV1
        django_get_or_create = ('email',)

    first_name = factory.Sequence(lambda x: 'Cont{:03d}'.format(x))
    last_name = factory.Sequence(lambda x: 'Act{:03d}'.format(x))
    company_name = factory.Sequence(lambda x: 'BigCorp{:03d}'.format(x))
    address = factory.SubFactory(AddressV1Factory)
    email = factory.LazyAttribute(lambda obj: u'{0.first_name}.{0.last_name}@example.com'.format(obj))
    phone = FuzzyPhoneNumber()


class sampleTeamV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = sampleTeamV1

    coordinator = factory.SubFactory(CoordinatorFactory)
    specialist = factory.SubFactory(SpecialistFactory)
    realtor = factory.SubFactory(RealtorFactory)


class LoanProfileV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = LoanProfileV1

    advisor = factory.SubFactory(AdvisorFactory)
    customer = factory.SubFactory(CustomerFactory)
    uniquifier = factory.LazyAttribute(lambda obj: str(hash(obj))[-8:])
    how_title_will_be_held = factory.fuzzy.FuzzyChoice(choices=HOW_TITLE_HELD_CHOICES)
    how_estate_will_be_held = factory.fuzzy.FuzzyChoice(choices=HOW_ESTATE_HELD_CHOICES)
    leasehold_expiration_date = FuzzyFutureDate(35, 45)
    base_loan_amount = factory.fuzzy.FuzzyDecimal(150000, 750000, precision=2)
    property_value_estimated = factory.fuzzy.FuzzyDecimal(150000, 750000, precision=2)


class LoanProfileV1EncompassSyncedFactory(LoanProfileV1Factory):
    encompass_sync_status = LoanProfileV1.ENCOMPASS_SYNCED
    los_guid = factory.fuzzy.FuzzyDecimal(150000, 750000, precision=2)


class LoanV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = LoanV1
        django_get_or_create = ('loan_id',)

    loan_id = factory.LazyAttribute(lambda _x: '{{{0}}}'.format(uuid.uuid4()))
    loan_profile = factory.SubFactory(LoanProfileV1Factory)
    property_address = factory.SubFactory(AddressV1Factory)
    lock_date = FuzzyFutureDate(LOCK_DAYS_MIN, LOCK_DAYS_MAX)
    lock_days = factory.fuzzy.FuzzyInteger(LOCK_DAYS_MIN, LOCK_DAYS_MAX)
    lender_name = factory.fuzzy.FuzzyText(length=6, suffix=u' Savings and Loan')
    product = factory.fuzzy.FuzzyText(length=8, suffix=u' Loan Product')
    loan_amount = factory.fuzzy.FuzzyDecimal(150000, 750000, precision=2)
    # interest_rate = factory.fuzzy.FuzzyDecimal(INTEREST_RATE_MIN, INTEREST_RATE_MAX, precision=3)
    # purchase_price = factory.fuzzy.FuzzyDecimal(INTEREST_RATE_MIN, INTEREST_RATE_MAX)
    target_close_date = factory.LazyAttribute(lambda x: x.lock_date + datetime.timedelta(LOAN_TARGET_CLOSE_DATE_OFFSET))


class EmploymentV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = EmploymentV1

    company_name = factory.fuzzy.FuzzyText(length=6, suffix=u' Software')
    company_address = factory.SubFactory(AddressV1Factory)
    phone = FuzzyPhoneNumber()
    title = factory.fuzzy.FuzzyText(length=8, suffix=u' Archeologist')
    start_date = FuzzyAgeDate(START_DATE_END, START_DATE_BEGIN)
    end_date = factory.fuzzy.FuzzyDate(datetime.date.today())
    years_in_field = factory.fuzzy.FuzzyInteger(YEARS_IN_FIELD_MIN, YEARS_IN_FIELD_MAX)
    is_self_employed = FuzzyBoolean()


class DemographicsV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = DemographicsV1

    ethnicity = factory.fuzzy.FuzzyChoice(choices=ETHNICITY_CHOICES)
    race = FuzzyArraySample(population=DemographicsV1.RACES._db_values)
    gender = factory.fuzzy.FuzzyChoice(choices=GENDER_CHOICES)
    is_us_citizen = FuzzyBoolean()
    is_permanent_resident_alien = FuzzyBoolean()
    is_party_to_lawsuit = FuzzyBoolean()
    is_party_to_lawsuit_explanation = FuzzyBoolean()
    is_obligated_to_pay_alimony_or_separate_maintenance = FuzzyBoolean()
    is_obligated_to_pay_alimony_or_separate_maintenance_explanation = FuzzyBoolean()
    is_any_part_of_downpayment_borrowed = FuzzyBoolean()
    is_any_part_of_downpayment_borrowed_explanation = FuzzyBoolean()
    is_comaker_or_endorser_on_note = FuzzyBoolean()
    is_comaker_or_endorser_on_note_explanation = factory.fuzzy.FuzzyText(length=8)
    is_delinquent_on_debt_presently = FuzzyBoolean()
    is_delinquent_on_debt_presently_explanation = factory.fuzzy.FuzzyText(length=8)
    has_outstanding_judgements = FuzzyBoolean()
    has_outstanding_judgements_explanation = factory.fuzzy.FuzzyText(length=8)
    has_declared_bankruptcy_within_past_seven_years = FuzzyBoolean()
    has_declared_bankruptcy_within_past_seven_years_explanation = factory.fuzzy.FuzzyText(length=8)
    has_property_foreclosed_within_past_seven_years = FuzzyBoolean()
    has_property_foreclosed_within_past_seven_years_explanation = factory.fuzzy.FuzzyText(length=8)
    has_been_obligated_on_resulted_in_foreclosure_loan = FuzzyBoolean()
    has_been_obligated_on_resulted_in_foreclosure_loan_explanation = factory.fuzzy.FuzzyText(length=8)
    has_ownership_interest_in_property_last_three_years = FuzzyBoolean()
    plans_to_occupy_as_primary_residence = FuzzyBoolean()
    owned_property_title_hold = factory.fuzzy.FuzzyChoice(PREVIOUS_PROPERTY_TITLE_HELD_CHOICES.keys())
    owned_property_type = factory.fuzzy.FuzzyChoice(PREVIOUS_PROPERTY_TYPE_CHOICES.keys())
    is_demographics_questions_request_confirmed = FuzzyBoolean()
    are_ethnicity_questions_skipped = FuzzyBoolean()


class BaseHoldingAssetV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = HoldingAssetV1


class VehicleAssetV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = VehicleAssetV1


class InsuranceAssetV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = InsuranceAssetV1


class ExpenseV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = ExpenseV1


class BaseLiabilityV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = LiabilityV1


class IncomeV1Factory(factory.DjangoModelFactory):
    class Meta:
        model = IncomeV1


class BorrowerBaseV1Factory(factory.DjangoModelFactory):
    class Meta:
        abstract = True

    ssn = FuzzySsn()
    dob = FuzzyAgeDate(BORROWER_AGE_MIN, BORROWER_AGE_MAX)
    email = factory.LazyAttribute(lambda x: u'{}.{}@example.com'.format(x.first_name, x.last_name))
    first_name = factory.fuzzy.FuzzyChoice(FIRST_NAME_CHOICES)
    middle_name = factory.fuzzy.FuzzyChoice(MIDDLE_NAME_CHOICES)
    last_name = factory.fuzzy.FuzzyChoice(LAST_NAME_CHOICES)
    title_name = factory.LazyAttribute(lambda x: force_text(u'{0.first_name} {0.middle_name} {0.last_name}'.format(x)))
    home_phone = FuzzyPhoneNumber()

    # Relationship fields
    mailing_address = factory.SubFactory(AddressV1Factory)
    demographics = factory.SubFactory(DemographicsV1Factory)
    realtor = factory.SubFactory(ContactV1Factory)

    # Many-to-Many fields
    @factory.post_generation
    def previous_addresses(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'previous_addresses', create, extracted, **kwargs)

    @factory.post_generation
    def previous_employment(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'previous_employment', create, extracted, **kwargs)

    @factory.post_generation
    def holding_assets(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'holding_assets', create, extracted, **kwargs)

    @factory.post_generation
    def vehicle_assets(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'vehicle_assets', create, extracted, **kwargs)

    @factory.post_generation
    def insurance_assets(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'insurance_assets', create, extracted, **kwargs)

    @factory.post_generation
    def income(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'income', create, extracted, **kwargs)

    @factory.post_generation
    def expense(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'expense', create, extracted, **kwargs)

    @factory.post_generation
    def liabilities(self, create, extracted, **kwargs):
        many_to_many_create_hook(self, 'liabilities', create, extracted, **kwargs)


class BorrowerV1Factory(BorrowerBaseV1Factory):
    class Meta:
        model = BorrowerV1
    current_property_type = factory.fuzzy.FuzzyChoice(PROPERTY_TYPE_CHOICES)
    properties_owned_count = 0
    ordering = factory.Sequence(lambda x: x)
    rent_or_own = False  # this means they rent


class CoborrowerV1Factory(BorrowerBaseV1Factory):
    class Meta:
        model = CoborrowerV1

    borrower = factory.SubFactory(BorrowerV1Factory)


# Assets
class CheckingAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'checking'


class CodAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'certificate_of_deposit'


class CashManagementAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'cash_management_account'


class FourOhOneKayAccountFactory(BaseHoldingAssetV1Factory):
    kind = '401k'


class InsuranceAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'insurance'


class IraAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'investment'


class InvestmentBrokerageAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'investment_brokerage'


class MoneyMarketAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'money_market'


class SavingsAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'savings'


class TrustAccountFactory(BaseHoldingAssetV1Factory):
    kind = 'trust'


# NOTE: not a holding account
class InvestmentFactory(BaseHoldingAssetV1Factory):
    kind = FuzzyPrefixedFloat('investment')


# Income
class BaseIncomeFactory(IncomeV1Factory):
    kind = IncomeV1.BASE


class BonusIncomeFactory(IncomeV1Factory):
    kind = IncomeV1.BONUS


class CommissionIncomeFactory(IncomeV1Factory):
    kind = IncomeV1.COMMISSION


class DividendIncomeFactory(IncomeV1Factory):
    kind = IncomeV1.DIVIDEND


class NetRentalIncomeFactory(IncomeV1Factory):
    kind = IncomeV1.NET_RENTAL


class OtherIncomeFactory(IncomeV1Factory):
    kind = IncomeV1.OTHER


class OvertimeIncomeFactory(IncomeV1Factory):
    kind = IncomeV1.OVERTIME


# Expenses
class FirstMortgageExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.FIRST_MORTGAGE


class HazardInsuranceExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.HAZARD_INSURANCE


class HoaExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.HOA


class MortgageInsuranceExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.MORTGAGE_INSURANCE


class OtherExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.OTHER


class OtherFinancingExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.OTHER_FINANCING


class RealEstateExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.REAL_ESTATE


class RentExpenseFactory(ExpenseV1Factory):
    kind = ExpenseV1.RENT


# Liabilities
class ChildCareLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.CHILD_CARE


class ChildSupportLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.CHILD_SUPPORT


class CollectionsJudgmentsAndLiensLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.COLLECTIONS_JUDGMENTS_AND_LIENS


class HelocLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.HELOC


class InstallmentLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.INSTALLMENT


class LeasePaymentsLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.LEASE_PAYMENTS


class MortgageLoanLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.MORTGAGE_LOAN


class Open30DaysChargeAccountLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.OPEN_30_DAYS_CHARGE_ACCOUNT


class OtherExpenseLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.OTHER_EXPENSE


class OtherLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.OTHER_LIABILITY


class RevolvingLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.REVOLVING


class SeparateMaintenanceExpenseLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.SEPARATE_MAINTENANCE_EXPENSE


class TaxesLiabilityFactory(BaseLiabilityV1Factory):
    kind = LiabilityV1.TAXES


class PurchaseLoanProfileFactory(LoanProfileV1Factory):
    purpose_of_loan = 'purchase'
    down_payment_amount = '125000'
    new_property_info_contract_purchase_price = '600000'
    new_property_address = factory.SubFactory(AddressV1Factory)


class RefinanceOtherLoanProfileFactory(LoanProfileV1Factory):
    purpose_of_loan = 'refinance'
    is_refinancing_current_address = False
    purpose_of_refinance = factory.fuzzy.FuzzyChoice(PURPOSE_OF_REFINANCE_CHOICES)
    new_property_address = factory.SubFactory(AddressV1Factory)
