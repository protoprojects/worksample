from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created, dispatch_uid="create_pgcrypto_extension")
def create_pgcrypto_extension(sender, **kwargs):
    from django.db import connection
    cur = connection.cursor()
    cur.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')
