# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-04-14 09:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_customerprotectedproxymodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='phoneverification',
            name='email',
            field=models.EmailField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='phoneverification',
            name='phone',
            field=models.CharField(max_length=255),
        ),
    ]
