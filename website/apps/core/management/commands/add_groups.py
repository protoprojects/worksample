from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.models import Advisor

class Command(BaseCommand):
    help = "Creates a sample advsior and a user group mortgage_advisors."

    def handle(self, *args, **options):
        """Creates an advisor for use in testing the application."""
        # TODO: set a prompt for user pw on creation? Or use args?
        group, group_created = Group.objects.get_or_create(name='mortgage_advisors')
        if group_created:
            self.stdout.write('Group: morgage_advisors created.')
        else:
            self.stdout.write('Group: morgage_advisors already exists, adding advisor ....')

        user = Advisor.objects.create(
            first_name='Misty',
            last_name='Shore',
            email='advisor@example.com',
            title='Greatest Morgage Advisor',
            is_staff=True,
        )
        user.groups.add(group)
        user.save()

        self.stdout.write('Advisor user and mortgage_advisors group complete.')
