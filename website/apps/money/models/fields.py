from django.db import models
from django.utils.encoding import force_text

from money.objects import Money


class CurrencyField(models.CharField):
    def __init__(self, default, price_field=None, verbose_name=None,
                 name=None, **kwargs):
        kwargs['max_length'] = 3
        self.price_field = price_field
        super(CurrencyField, self).__init__(verbose_name, name, default=default,
                                            **kwargs)

    def get_internal_type(self):
        return "CharField"

    def contribute_to_class(self, cls, name, virtual_only=False):
        # pylint: disable=protected-access
        if name not in [f.name for f in cls._meta.fields]:
            super(CurrencyField, self).contribute_to_class(cls, name)


class MoneyFieldProxy(object):
    """
    Proxy is used to set amount and currency properly.
    There are two cases:
    * We set only value (currency will be default in that case)
    * We set amount and currency with `Money` class (currency will be taken from class)
    """

    def __init__(self, field):
        self.field = field
        self.currency_field_name = "%s_currency" % self.field.name

    def __set__(self, obj, value):
        if isinstance(value, Money):
            obj.__dict__[self.field.name] = value.amount
            setattr(obj, self.currency_field_name, force_text(value.currency))
        else:
            if value:
                value = str(value)
            obj.__dict__[self.field.name] = self.field.to_python(value)


class MoneyField(models.DecimalField):
    def __init__(self, default_currency, verbose_name=None, name=None,
                 max_digits=None, decimal_places=None, default=None, **kwargs):
        self.default_currency = default_currency

        if decimal_places is None:
            raise Exception("decimal_places must be provided.")
        if max_digits is None:
            raise Exception("max_digits must be provided.")

        super(MoneyField, self).__init__(verbose_name, name, max_digits,
                                         decimal_places, default=default,
                                         **kwargs)

    def get_internal_type(self):
        return "DecimalField"

    def contribute_to_class(self, cls, name, virtual_only=False):
        # pylint: disable=protected-access
        cls._meta.has_money_field = True
        c_field_name = "%s_currency" % name
        c_field = CurrencyField(
            max_length=3,
            price_field=self,
            default=self.default_currency,
            editable=False,
        )
        cls.add_to_class(c_field_name, c_field)
        super(MoneyField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, MoneyFieldProxy(self))

    def deconstruct(self):
        name, path, args, kwargs = super(MoneyField, self).deconstruct()
        if self.default:
            kwargs['default'] = self.default
        kwargs['default_currency'] = self.default_currency
        return name, path, args, kwargs

    def to_python(self, value):
        if isinstance(value, Money):
            value = value.amount
        return super(MoneyField, self).to_python(value)

    def get_db_prep_save(self, value, connection):
        if isinstance(value, Money):
            value = value.amount
        return super(MoneyField, self).get_db_prep_save(value, connection)
