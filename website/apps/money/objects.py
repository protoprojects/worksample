import decimal


class Money(object):
    """
    A Money instance is a combination of data:
    an amount and a currency.
    """

    def __init__(self, amount, currency):
        if not isinstance(amount, decimal.Decimal):
            amount = decimal.Decimal(str(amount))
        self.amount = amount
        if not isinstance(currency, str):
            raise AttributeError('Currency must be string')
        self.currency = currency
