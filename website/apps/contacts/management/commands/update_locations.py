import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from contacts.models import Location


class Command(BaseCommand):
    help = 'Update locations cache from http://www.unitedstateszipcodes.org/zip-code-database/'

    def handle(self, *args, **options):
        file_path = os.path.join(os.path.dirname(settings.PROJECT_PATH), 'assets', 'zip_code_database.csv')

        if len(Location.objects.all()) > 0:
            self.stdout.write("Locations already created.")
            return

        with open(file_path) as contents:
            reader = csv.reader(contents)
            for line in reader:
                zipcode, city, state, county = line[0], line[2], line[5], line[6]
                Location.objects.update_or_create(zipcode=zipcode, city=city, state=state, county=county)
            self.stdout.write('Done!')
