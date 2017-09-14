from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Recaptcha


class Command(BaseCommand):
    """
    Configure Recaptcha. Requires configuration of the follow environment variables:
    * RECAPTCHA_ENABLED (default=True)
    * RECAPTCHA_SITE_KEY
    * RECAPTCHA_SECRET_KEY
    * RECAPTCHA_VERIFICATION_URL
    """
    help = '''Configure Recaptcha. Requires configuration of the following environment variables:
        RECAPTCHA_ENABLED (default=True), RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY, RECAPTCHA_VERIFICATION_URL'''

    def handle(self, *args, **options):
        Recaptcha.objects.update_or_create(
            enable=settings.RECAPTCHA_ENABLED or True,
            site_key=settings.RECAPTCHA_SITE_KEY,
            secret_key=settings.RECAPTCHA_SECRET_KEY,
            verification_url=settings.RECAPTCHA_VERIFICATION_URL
        )
        self.stdout.write('Recaptcha update complete!')
