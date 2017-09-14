from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='accounts.Advisor')
def advisor_post_save_callback(sender, **kwargs):
    from box.api_v1 import advisor_loan_storage_update
    if settings.ADVISOR_STORAGE_HOOK_ENABLE:
        advisor = kwargs['instance']
        advisor_loan_storage_update(advisor)
