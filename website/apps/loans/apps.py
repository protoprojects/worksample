from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def create_notice_types(sender, **kwargs):
    if "pinax.notifications" in settings.INSTALLED_APPS:
        from pinax.notifications.models import NoticeType

        NoticeType.create(
            "advisor_assignment",
            "Advisor Assignment",
            "Advisor Assignment"
        )
        NoticeType.create(
            "advisor_request_fallback",
            "Default Advisor Assigned",
            "Default Advisor Assigned"
        )
        NoticeType.create(
            "coborrower_verification",
            "Coborrower Verification",
            "Coborrower Verification"
        )
        NoticeType.create(
            "coborrower_verify",
            "Coborrower Verified",
            "Coborrower Verified"
        )
        NoticeType.create(
            "coborrower_decline",
            "Coborrower Declined",
            "Coborrower Declined"
        )
        NoticeType.create(
            "advisor_coborrower_decline",
            "Advisor Coborrower Decline",
            "Advisor Coborrower Decline"
        )
        NoticeType.create(
            "advisor_respa",
            "Advisor RESPA Trigger Notification",
            "Advisor RESPA Trigger Notification"
        )
    else:
        print "Skipping creation of NoticeTypes in Loans - notification app not found"


class LoansConfig(AppConfig):
    name = 'loans'
    verbose_name = "Loans"

    def ready(self):
        post_migrate.connect(create_notice_types, sender=self)
