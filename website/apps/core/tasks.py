import os

from django.conf import settings
from django.core.management import call_command
from celery import shared_task, task


@shared_task
def send_message(message, notice_type_label=None):
    """
    Async sending django email
    Returns result of send, recipients, notice type label

    """

    return message.send(), message.recipients(), notice_type_label


@task
def dbbackup():
    os.environ['PGPASSWORD'] = settings.DATABASES['default']['PASSWORD']
    call_command('dbbackup', compress=True)
