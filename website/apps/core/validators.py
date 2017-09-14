from django.core.validators import BaseValidator

class MyMaxValueValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    message = 'Ensure this value is less than or equal to %(limit_value)s.'

    def __init__(self, limit_value, message=None):
        self.limit_value = limit_value
        if message:
            self.message = message

class MyMinValueValidator(BaseValidator):
    compare = lambda self, a, b: a < b
    message = 'Ensure this value is greater than or equal to %(limit_value)s.'

    def __init__(self, limit_value, message=None):
        self.limit_value = limit_value
        if message:
            self.message = message
