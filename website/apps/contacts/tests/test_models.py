from django.core.exceptions import ValidationError
from django.test import TestCase

from contacts import models


class ContactRequestUnlicensedStateTests(TestCase):
    def test_saves_correct_defaults(self):
        cr = models.ContactRequestUnlicensedState.objects.create()
        self.assertEqual(cr.kind, 'unlicensed_state')
        self.assertEqual(cr.unlicensed_state_code, None)

    def test_saves_valid_state_saves(self):
        cr = models.ContactRequestUnlicensedState.objects.create(unlicensed_state_code='CA')
        self.assertEqual(cr.kind, 'unlicensed_state')
        self.assertEqual(cr.unlicensed_state_code, 'CA')

    def test_cannot_save_incorrect_data(self):
        bad_data = ['ca', 'hello', 'California']
        cr = models.ContactRequestUnlicensedState.objects.create()
        for datum in bad_data:
            with self.assertRaises(ValidationError):
                cr.unlicensed_state_code = datum
                cr.full_clean()

    def test_cannot_save_blank(self):
        with self.assertRaises(ValidationError):
            cr = models.ContactRequestUnlicensedState.objects.create(unlicensed_state_code='')
            cr.full_clean()
