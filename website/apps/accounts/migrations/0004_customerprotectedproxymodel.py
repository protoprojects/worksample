# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-04-13 13:53
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_advisor_nmls_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerProtectedProxyModel',
            fields=[
            ],
            options={
                'verbose_name': 'Customer',
                'proxy': True,
            },
            bases=('accounts.customer',),
        ),
    ]