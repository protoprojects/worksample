import subprocess

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from storage.models import Storage


class Command(BaseCommand):
    help = 'Create a backup of the schema for the application. Valid extensions: .dump, .dmp, .sql'
    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('db_name', nargs='+', type=str, help='Name of the target database.')

        # Named (optional) arguments, start with - or --
        parser.add_argument(
            '--ext',
            action='store',
            choices=['dump', 'dmp', 'sql'],
            dest='extension',
            help='File extension of the output file: dump, dmp, or sql'
        )
        # TODO: Implement dumping tables for specific apps.
        # parser.add_argument(
        #     '-t',
        #     action='store',
        #     dest='table',
        #     help='List of tables to dump. To dump all tables for a specifc app use: `public.appname*` where appname is the app name.'
        # )

    def handle(self, *args, **options):
        db_name = options['db_name'][0]
        date = str(datetime.today().date())
        file_name = 'backup-' + db_name + date
        ext = 'dump'
        if options['extension']:
            ext = options['extension'][0]

        cmd = 'pg_dump -s {0} -O > dumps/{1}.{2}'.format(db_name, file_name, ext)
        # TODO: Enable dumping specific app table schemas.
        # if options['table']:
        #     table = options['table'][0]
        #     cmd = 'pg_dump -t "{2}" -s {0} -O > {1}.dump'.format(db_name, file_name, table)
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write("{0} \n Make sure you have a dumps/ directory in this folder and add it to your global gitignore.".format(e))
            return
        else:
            self.stdout.write('Backup for {0} complete.'.format(db_name))
