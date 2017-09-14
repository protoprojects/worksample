# -*- coding: utf-8 -*-
import decimal

from django.db import models

from money.models.fields import MoneyField


class TestMoneyModel(models.Model):
    money_field_1 = MoneyField(
        blank=True,
        null=True,
        default_currency='USD',
        max_digits=10,
        decimal_places=2,
        default=None
    )
    money_field_2 = MoneyField(
        default_currency='USD',
        max_digits=10,
        decimal_places=2,
        default=decimal.Decimal('150000.0')
    )
