# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-03-13 21:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mortgage_profiles', '0004_auto_20170308_0158'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mortgageprofile',
            name='conversion_url',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='mortgageprofile',
            name='referral_url',
            field=models.TextField(blank=True),
        ),
    ]
