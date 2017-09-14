# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-02-02 00:07
from __future__ import unicode_literals

import core.utils
from django.db import migrations
import functools
import shortuuidfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('mortgage_profiles', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mortechrequest',
            name='uuid',
            field=shortuuidfield.fields.ShortUUIDField(blank=True, default=functools.partial(core.utils.create_shortuuid, *(), **{}), editable=False, max_length=22, unique=True),
        ),
        migrations.AlterField(
            model_name='mortgageprofile',
            name='uuid',
            field=shortuuidfield.fields.ShortUUIDField(blank=True, default=functools.partial(core.utils.create_shortuuid, *(), **{}), editable=False, max_length=22, unique=True),
        ),
    ]