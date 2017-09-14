from __future__ import absolute_import

import os

from celery import Celery
from raven import Client
from raven.contrib.celery import register_signal

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings.dev')

app = Celery('sample')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


if getattr(settings, 'RAVEN_CONFIG', None):
    os.environ.setdefault('SENTRY_DSN', settings.RAVEN_CONFIG['dsn'])

    client = Client()
    register_signal(client)
