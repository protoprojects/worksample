# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-03-22 23:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employmentv1',
            name='is_current_employment',
            field=models.NullBooleanField(),
        ),
    ]