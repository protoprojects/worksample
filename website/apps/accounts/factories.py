# coding: utf-8
import factory
import factory.fuzzy

from accounts.models import Advisor, Coordinator, Customer, Realtor, Specialist, User, PhoneVerification, \
    CustomerEmailValidation


USER_PASSWORD = 'secret'


class BaseUserFactoryMixin(factory.DjangoModelFactory):
    class Meta:
        django_get_or_create = ('email',)

    first_name = factory.fuzzy.FuzzyText(length=4, prefix='test')
    last_name = factory.fuzzy.FuzzyText(length=4, prefix='user')
    email = factory.LazyAttribute(lambda x: '{}.{}@example.com'.format(x.first_name, x.last_name))
    password = factory.PostGenerationMethodCall('set_password', USER_PASSWORD)


class BasesampleUserFactoryMixin(BaseUserFactoryMixin):
    email = factory.LazyAttribute(lambda x: '{}.{}@sample.example.com'.format(x.first_name, x.last_name))


class AdvisorFactory(BasesampleUserFactoryMixin):
    class Meta:
        model = Advisor
    last_name = factory.Sequence('adv{:03d}'.format)


class CustomerFactory(BaseUserFactoryMixin):
    class Meta:
        model = Customer

    # pylint: disable=protected-access
    phone_kind = factory.fuzzy.FuzzyChoice(Customer.PHONE_KINDS._db_values)


class CoordinatorFactory(BasesampleUserFactoryMixin):
    class Meta:
        model = Coordinator
    last_name = factory.Sequence('coord{:03d}'.format)


class RealtorFactory(BaseUserFactoryMixin):
    class Meta:
        model = Realtor
    last_name = factory.Sequence('real{:03d}'.format)


class SpecialistFactory(BasesampleUserFactoryMixin):
    class Meta:
        model = Specialist
    last_name = factory.Sequence('spec{:03d}'.format)


class UserFactory(BaseUserFactoryMixin):
    class Meta:
        model = User


class PhoneVerificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = PhoneVerification


class CustomerEmailValidationFactory(factory.DjangoModelFactory):
    class Meta:
        model = CustomerEmailValidation
