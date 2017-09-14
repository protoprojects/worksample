import subprocess

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Truncate database tables.

    Differs from django-admin flush in that it clears django_migrations as well. This command also preserves
    users and owners of the current database tables.
    """
    help = 'Clear (truncate) all database tables for the application.'
    args = 'db_name'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('db_name', nargs='+', type=str, help='Name of the target database.')

    def handle(self, *args, **options):
        db_name = options['db_name'][0]

        # Backup schema
        self.stdout.write("Backing up {} schema ...".format(db_name))
        subprocess.call(['pg_dump', '-s', '-f', db_name], shell=True)

        # Drop datbase
        self.stdout.write("Dropping {} ...".format(db_name))
        subprocess.call(['dropdb', db_name], shell=True)

        # Re-create database
        self.stdout.write("Re-creating {}...".format(db_name))
        subprocess.call(['createdb', db_name], shell=True)

        # Restore schema
        self.stdout.write("Restoring {} schema...".format(db_name))
        subprocess.call(['pg_restore', dump_name, '>', 'psql', db_name], shell=True)

        self.stdout.write('{0} data reset complete. All tables now have 0 rows.'.format(db_name))
