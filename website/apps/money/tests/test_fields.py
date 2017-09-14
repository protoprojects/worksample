import decimal
from unittest import skipUnless

from django.conf import settings
from django.test import TestCase

from money.objects import Money


@skipUnless(settings.TEST_APPLICATIONS_ENABLED, reason='Custom application running skipped.')
class MoneyFieldTests(TestCase):
    # pylint: disable=protected-access
    def test_all_fields_were_created_correctly(self):
        from money.tests.test_money_app.models import TestMoneyModel
        concrete_fields = TestMoneyModel._meta.concrete_fields
        money_field1 = TestMoneyModel._meta.get_field('money_field_1')
        money_field2 = TestMoneyModel._meta.get_field('money_field_2')
        currency_field1 = TestMoneyModel._meta.get_field('money_field_1_currency')
        currency_field2 = TestMoneyModel._meta.get_field('money_field_2_currency')
        self.assertIn(money_field1, concrete_fields)
        self.assertIn(money_field2, concrete_fields)
        self.assertIn(currency_field1, concrete_fields)
        self.assertIn(currency_field2, concrete_fields)

    def test_field_defaults(self):
        from money.tests.test_money_app.models import TestMoneyModel
        obj = TestMoneyModel.objects.create()
        self.assertEqual(obj.money_field_1, None)
        self.assertEqual(obj.money_field_2, decimal.Decimal('150000.0'))

    def test_save_some_value(self):
        from money.tests.test_money_app.models import TestMoneyModel
        obj = TestMoneyModel()
        obj.money_field_1 = decimal.Decimal('1')
        obj.money_field_2 = decimal.Decimal('123')
        obj.save()
        saved_obj = TestMoneyModel.objects.get(id=obj.id)
        self.assertEqual(saved_obj.money_field_1, decimal.Decimal('1'))
        self.assertEqual(saved_obj.money_field_2, decimal.Decimal('123'))
        self.assertEqual(saved_obj.money_field_1_currency, 'USD')
        self.assertEqual(saved_obj.money_field_2_currency, 'USD')

    def test_save_value_from_money_obj(self):
        from money.tests.test_money_app.models import TestMoneyModel
        obj = TestMoneyModel()
        obj.money_field_1 = Money(amount=13, currency='USD')
        obj.money_field_2 = Money(amount=666, currency='UAH')
        obj.save()
        saved_obj = TestMoneyModel.objects.get(id=obj.id)
        self.assertEqual(saved_obj.money_field_1_currency, 'USD')
        self.assertEqual(saved_obj.money_field_2_currency, 'UAH')
