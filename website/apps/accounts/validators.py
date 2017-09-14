from __future__ import unicode_literals

import json
import logging
from os.path import join
import jsonschema

from django.core.exceptions import ValidationError

from website.settings.utils import PROJECT_PATH

logger = logging.getLogger('sample.accounts.validators')

SCHEMA_PATH = join(PROJECT_PATH, 'apps/accounts/contact_preferences_schema.json')


def validate_contact_preferences(preferences):
    """
    Validates the preferences of a contact

    :param preferences: a JSON blob containing the preferences to be validated
    :raises ValidationError: if the JSON schema is invalid or if any preferences fail validation
    """
    try:
        with open(SCHEMA_PATH) as schema_data:
            schema = json.load(schema_data)
            errors = []
            for error in sorted(jsonschema.Draft4Validator(schema).iter_errors(preferences)):
                errors.append(error.message)
            if errors != []:
                raise ValidationError(errors)
    except jsonschema.SchemaError as exc:
        logger.exception('CONTACT-PREFERENCES-SCHEMA-ERROR')
        raise ValidationError(exc)


class PasswordValidator(object):
    """Class to validate passwords"""
    message = 'Must be more complex (%s)'
    code = 'complexity'

    LETTERS = 'LETTERS'
    UPPER = 'UPPER'
    LOWER = 'LOWER'
    DIGITS = 'DIGITS'
    SPECIAL = 'SPECIAL'
    MIN_LENGTH = 'MIN_LENGTH'

    def __init__(self, **kwargs):
        self.requirements = {
            self.LETTERS: kwargs.get(self.LETTERS, 0),
            self.UPPER: kwargs.get(self.UPPER, 0),
            self.LOWER: kwargs.get(self.LOWER, 0),
            self.DIGITS: kwargs.get(self.DIGITS, 0),
            self.SPECIAL: kwargs.get(self.SPECIAL, 0),
            self.MIN_LENGTH: kwargs.get(self.MIN_LENGTH, 0),
        }

    def __call__(self, password):
        if self.requirements is None:
            return

        errors = []
        if len(password) < self.requirements[self.MIN_LENGTH]:
            errors.append('minimum length of %(MIN_LENGTH)s characters' % self.requirements)

        letters, uppercase, lowercase, digits, special = set(), set(), set(), set(), set()

        for character in password:
            if character.isalpha():
                letters.add(character)
                if character.isupper():
                    uppercase.add(character)
                else:
                    lowercase.add(character)
            elif character.isdigit():
                digits.add(character)
            elif not character.isspace():
                special.add(character)

        if len(letters) < self.requirements[self.LETTERS]:
            errors.append('%(LETTERS)s or more unique letters' % self.requirements)
        if len(uppercase) < self.requirements[self.UPPER]:
            errors.append('%(UPPER)s or more unique uppercase characters' % self.requirements)
        if len(lowercase) < self.requirements[self.LOWER]:
            errors.append('%(LOWER)s or more unique lowercase characters' % self.requirements)
        if len(digits) < self.requirements[self.DIGITS]:
            errors.append('%(DIGITS)s or more unique digits' % self.requirements)
        if len(special) < self.requirements[self.SPECIAL]:
            errors.append('%(SPECIAL)s or more unique special characters' % self.requirements)

        if errors:
            raise ValidationError(self.message % (u'must contain ' + u', '.join(errors),),
                                  code=self.code)
