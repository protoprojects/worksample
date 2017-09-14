from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    """
    Set-up your sample environment with:
    * Recaptcha
    * State Licenses
    * Groups
    * Locations (zipcodes)

    """
    help = 'Configure the app with locations, licenses, groups and recaptcha.'

    def handle(self, *args, **options):
        # State licenses
        self.stdout.write("Creating state licenses...")
        call_command('update_licenses')

        # Box storage
        # TODO: Needs storage IDs so command needs ARGS or use env variables
        # self.stdout.write("Adding Box storages...")
        # call_command('create_base_storages')

        # Recaptcha
        self.stdout.write("Updating Recaptcha...")
        call_command('update_recaptcha')

        # Mortgage advisor groups
        self.stdout.write("Creating mortgage advisor groups...")
        call_command('add_groups')

        # Locations
        self.stdout.write("Adding locations (this takes few minutes)...")
        call_command('update_locations')

        self.stdout.write('sample setup complete!')
