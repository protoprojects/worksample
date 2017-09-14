from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def create_notice_types(sender, **kwargs):
    if "pinax.notifications" in settings.INSTALLED_APPS:
        from pinax.notifications.models import NoticeType

        NoticeType.create(
            "reset_password",
            "Reset password",
            "Reset password"
        )
        NoticeType.create(
            "registration_new_user",
            "New user registered",
            "New user registered"
        )
        NoticeType.create(
            "registration_password_change",
            "Password changed",
            "Password changed"
        )
        NoticeType.create(
            "welcome_message",
            "Welcome Message",
            "Welcome Message"
        )
    else:
        print "Skipping creation of NoticeTypes in Accounts- notification app not found"


class AccountsConfig(AppConfig):
    name = 'accounts'
    verbose_name = "Accounts"

    def ready(self):
        post_migrate.connect(create_notice_types, sender=self)
