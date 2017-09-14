# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-01-11 00:11
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('storage', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BoxEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('box_event_type', models.CharField(choices=[(b'uploaded', b'Uploaded'), (b'deleted', b'Deleted')], db_index=True, max_length=20)),
                ('is_processed', models.BooleanField(default=False)),
                ('document_id', models.CharField(max_length=255)),
                ('box_user_id', models.CharField(max_length=255)),
                ('storage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='storage.Storage')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
