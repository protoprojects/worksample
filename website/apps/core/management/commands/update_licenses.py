import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from pages.models import StateLicense


class Command(BaseCommand):
    """
    Install state licenses to the database.
    """
    help = 'Add base state licenses.'

    def handle(self, *args, **options):
        file_path = os.path.join(os.path.dirname(settings.PROJECT_PATH), 'assets', 'statelicense_database.csv')

        with open(file_path) as contents:
            reader = csv.reader(contents)
            states = []
            for line in reader:
                state, license_type, license_number, end_date, description = line[0], line[1], line[2], line[3], line[4]
                print("Adding license for {0}...".format(state))

                StateLicense.objects.update_or_create(
                    state_name=state,
                    license_type=license_type,
                    license_number=license_number,
                    end_date=end_date,
                    description=description
                )
            self.stdout.write('Licenses updated.')
