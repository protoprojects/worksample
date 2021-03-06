# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-01-11 00:11
from __future__ import unicode_literals

import core.models
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import encrypted_fields.fields
import money.models.fields
import shortuuidfield.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('loans', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MortechLender',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('lender_name', models.CharField(max_length=255)),
                ('amortization_type', models.CharField(max_length=255)),
                ('apr', models.DecimalField(decimal_places=6, max_digits=10)),
                ('fees', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('monthly_premium', money.models.fields.MoneyField(decimal_places=2, default=None, default_currency=b'USD', max_digits=10)),
                ('piti', money.models.fields.MoneyField(decimal_places=2, default=None, default_currency=b'USD', max_digits=10, null=True)),
                ('points', models.DecimalField(decimal_places=6, max_digits=9)),
                ('price', models.DecimalField(decimal_places=6, max_digits=9, null=True)),
                ('program_category', models.CharField(blank=True, max_length=255)),
                ('program_name', models.CharField(max_length=255)),
                ('program_type', models.CharField(choices=[(b'VA', b'VA'), (b'FHA', b'FHA'), (b'Non Conforming', [b'Non Conf', b'Non Conforming']), (b'Conforming', [b'Conf', b'Conforming']), (b'Jumbo', b'Jumbo')], max_length=255)),
                ('rate', models.DecimalField(decimal_places=6, max_digits=10)),
                ('term', models.CharField(max_length=255)),
                ('upfront_fee', money.models.fields.MoneyField(decimal_places=2, default=None, default_currency=b'USD', max_digits=10, null=True)),
                ('upfront_fee_currency', money.models.fields.CurrencyField(default=b'USD', editable=False, max_length=3)),
                ('monthly_premium_currency', money.models.fields.CurrencyField(default=b'USD', editable=False, max_length=3)),
                ('piti_currency', money.models.fields.CurrencyField(default=b'USD', editable=False, max_length=3)),
            ],
            options={
                'ordering': ('-created',),
                'verbose_name': 'Mortech Lender',
                'verbose_name_plural': 'Mortech Lenders',
            },
        ),
        migrations.CreateModel(
            name='MortechRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('uuid', shortuuidfield.fields.ShortUUIDField(blank=True, default=b'MTD3JuwkfcAnot5W3wPSsk', editable=False, max_length=22, unique=True)),
            ],
            options={
                'ordering': ('-created',),
                'verbose_name': 'Mortech Request',
                'verbose_name_plural': 'All Mortech Requests',
            },
        ),
        migrations.CreateModel(
            name='MortgageProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('uuid', shortuuidfield.fields.ShortUUIDField(blank=True, default=b'5rKhnxRYQt4cbG8UL9wDya', editable=False, max_length=22, unique=True)),
                ('kind', models.CharField(choices=[(b'refinance', b'Refinance'), (b'purchase', b'Purchase')], max_length=255)),
                ('advisor_email', models.EmailField(blank=True, max_length=255)),
                ('adjustable_rate_comfort', models.CharField(blank=True, choices=[(b'yes', b'Yes'), (b'no', b'No'), (b'unsure', b'Not Sure')], max_length=255)),
                ('rate_preference', models.CharField(blank=True, choices=[(b'fixed', b'Fixed'), (b'variable', b'Variable')], max_length=255)),
                ('referrer_email', models.EmailField(blank=True, max_length=255)),
                ('referral_url', models.URLField(blank=True, max_length=1000)),
                ('conversion_url', models.URLField(blank=True, max_length=1000)),
                ('ownership_time', encrypted_fields.fields.EncryptedCharField(blank=True, choices=[(b'long_term', b'Long term / Quite a while'), (b'medium_term', b'Medium term  / 5-15 years'), (b'short_term', b'Short term / Only a few years'), (b'not_sure', b'Not Sure')], max_length=255)),
                ('credit_rating', encrypted_fields.fields.EncryptedCharField(blank=True, choices=[(b'0_579', b'Not so good (<579)'), (b'580_599', b'Needs Improvement (580-599)'), (b'600_619', b'Needs Improvement (600-619)'), (b'620_639', b'Fair (620-639)'), (b'640_659', b'Fair (640-659)'), (b'660_679', b'Fair (660-679)'), (b'680_699', b'Good (680-699)'), (b'700_719', b'Good (700-719)'), (b'720_739', b'Good (720-739)'), (b'740_759', b'Excellent (740-759)'), (b'760_', b'Excellent (760+)'), (b'dont_know', b"I don't know")], max_length=255)),
                ('hoa_dues', money.models.fields.MoneyField(blank=True, decimal_places=2, default=None, default_currency='USD', max_digits=10, null=True)),
                ('credit_score', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(850)])),
                ('is_veteran', core.models.EncryptedNullBooleanField()),
                ('property_zipcode', encrypted_fields.fields.EncryptedCharField(blank=True, max_length=255)),
                ('property_state', encrypted_fields.fields.EncryptedCharField(blank=True, max_length=255)),
                ('property_city', encrypted_fields.fields.EncryptedCharField(blank=True, max_length=255)),
                ('property_county', encrypted_fields.fields.EncryptedCharField(blank=True, max_length=255)),
                ('property_type', encrypted_fields.fields.EncryptedCharField(blank=True, choices=[(b'single_family', b'Single family residence'), (b'condo_less_5', b'Condo (<5 stories)'), (b'condo_5_8', b'Condo (5-8 stories)'), (b'condo_more_8', b'Condo (>8 stories)'), (b'townhouse', b'Townhouse'), (b'two_unit', b'Two-unit'), (b'three_unit', b'Three-unit'), (b'four_unit', b'Four-unit'), (b'manufactured_single', b'Manufactured singlewide'), (b'vacant_lot_land', b'Vacant Lot/Land'), (b'pud_has_hoa_dues', b'PUD/Has HOA dues')], max_length=255)),
                ('property_occupation', encrypted_fields.fields.EncryptedCharField(blank=True, max_length=255)),
                ('rate_quote_refresh_progress', models.CharField(blank=True, choices=[(b'in_progress', b'In Progress'), (b'complete', b'Complete')], max_length=255)),
                ('hoa_dues_currency', money.models.fields.CurrencyField(default='USD', editable=False, max_length=3)),
            ],
            options={
                'ordering': ('-created',),
                'verbose_name': 'Mortgage profile',
                'verbose_name_plural': 'All mortgage profiles',
            },
        ),
        migrations.CreateModel(
            name='MortgageProfilePurchase',
            fields=[
                ('mortgageprofile_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortgage_profiles.MortgageProfile')),
                ('purchase_timing', encrypted_fields.fields.EncryptedCharField(blank=True, choices=[(b'researching_options', b'Not sure / just researching'), (b'buying_in_3_months', b'Buying in the next 3 months'), (b'offer_submitted', b'House in mind / offer submitted'), (b'contract_in_hand', b'Purchase contract in hand')], max_length=255)),
                ('purchase_type', encrypted_fields.fields.EncryptedCharField(blank=True, choices=[(b'first_time_homebuyer', b'First Time Homebuyer'), (b'selling_home', b'Selling Home/Moving'), (b'vacation_home', b'Second Home/Vacation Home'), (b'investment_property', b'Investment Property')], max_length=255)),
                ('purchase_down_payment', encrypted_fields.fields.EncryptedIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(10000000)])),
                ('target_value', encrypted_fields.fields.EncryptedIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(10000), django.core.validators.MaxValueValidator(10000000)])),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Purchase mortgage profile',
                'verbose_name_plural': 'Purchase mortgage profiles',
            },
            bases=('mortgage_profiles.mortgageprofile',),
        ),
        migrations.CreateModel(
            name='MortgageProfileRefinance',
            fields=[
                ('mortgageprofile_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortgage_profiles.MortgageProfile')),
                ('purpose', encrypted_fields.fields.EncryptedCharField(blank=True, choices=[(b'lower_mortgage_payments', b'Lower mortgage rate or payment'), (b'cash_out', b'Tap into equity/cash out'), (b'heloc', b'Home equity line of credit'), (b'both', b'Both')], max_length=255)),
                ('property_value', encrypted_fields.fields.EncryptedIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(10000), django.core.validators.MaxValueValidator(10000000)])),
                ('mortgage_owe', encrypted_fields.fields.EncryptedIntegerField(blank=True, null=True)),
                ('mortgage_term', encrypted_fields.fields.EncryptedCharField(blank=True, choices=[(b'40_year', b'40 Year'), (b'30_year', b'30 Year'), (b'20_year', b'20 Year'), (b'15_year', b'15 Year'), (b'10_year', b'10 Year')], max_length=255)),
                ('mortgage_start_date', core.models.EncryptedDataField(blank=True, null=True)),
                ('mortgage_rate', encrypted_fields.fields.EncryptedIntegerField(blank=True, null=True)),
                ('mortgage_monthly_payment', encrypted_fields.fields.EncryptedIntegerField(blank=True, null=True)),
                ('cashout_amount', encrypted_fields.fields.EncryptedIntegerField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'Refinance mortgage profile',
                'verbose_name_plural': 'Refinance mortgage profiles',
            },
            bases=('mortgage_profiles.mortgageprofile',),
        ),
        migrations.AddField(
            model_name='mortgageprofile',
            name='loan_profilev1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mortgage_profiles', to='loans.LoanProfileV1'),
        ),
        migrations.AddField(
            model_name='mortgageprofile',
            name='selected_mortech_lender',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mortgage_profile', to='mortgage_profiles.MortechLender'),
        ),
        migrations.AddField(
            model_name='mortgageprofile',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mortgage_profiles', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mortechrequest',
            name='mortgage_profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mortechrequests', to='mortgage_profiles.MortgageProfile'),
        ),
        migrations.AddField(
            model_name='mortechlender',
            name='request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mortechlenders', to='mortgage_profiles.MortechRequest'),
        ),
    ]
