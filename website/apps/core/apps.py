from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def create_notice_types(*args, **kwargs):
    if "pinax.notifications" in settings.INSTALLED_APPS:
        from pinax.notifications.models import NoticeType
        NoticeType.create(
            "exception_notification",
            "Exception notification",
            "Exception notification",
        )


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = 'Core'

    def ready(self):
        # registering signals
        from core import signals  # pylint: disable=unused-variable

        post_migrate.connect(create_notice_types, sender=self)

        # FIXME: By some reason django-appconf, which is used
        #        pinax-notifications does not want to set configured
        #        data to the settings.
        from pinax.notifications.conf import PinaxNotificationsAppConf
        configured_data = PinaxNotificationsAppConf().configure()
        for k, v in configured_data.iteritems():
            setattr(settings, 'PINAX_NOTIFICATIONS_%s' % k, v)
