from django.apps import AppConfig
from django.conf import settings
from django.db.models import signals


def create_notice_types(sender, **kwargs):
    if "pinax.notifications" in settings.INSTALLED_APPS:
        from pinax.notifications.models import NoticeType

        NoticeType.create(
            "contact_request_new_user",
            "Contact request received",
            "Contact request received from new user"
        )

        NoticeType.create(
            "contact_request_existing_user",
            "Contact request received",
            "Contact request received from existing user"
        )

        NoticeType.create(
            "inquiry_no_account",
            "Consultation request received",
            "Consultation request received from new user"
        )

        NoticeType.create(
            "rate_quote_no_account",
            "complete rate quote contact form",
            "complete rate quote contact form (not existing user)"
        )

        NoticeType.create(
            "administrative_contact_request",
            "Contact request from rate quote for administrative",
            "Contact request administrative"
        )

        NoticeType.create(
            "administrative_inquiry",
            "Consultation form on home page",
            "Consultation form on home page"
        )

        NoticeType.create(
            "administrative_contact_request_about_us",
            "Contact request form 'about us' page",
            "Contact request form 'about us' page"
        )

        NoticeType.create(
            "admin_contact_request_unsupported_step",
            "Contact request from rate quote unsupported step",
            "Contact request unsupported step"
        )

        NoticeType.create(
            "inquiry_contact_us",
            "form completed on Contact Us page",
            "form completed on Contact Us page"
        )

        NoticeType.create(
            "inquiry_chat_message",
            "left a message on chat",
            "left a message on chat"
        )

        NoticeType.create(
            "admin_contact_request_partner",
            "Contact request from partner",
            "Contact request partner"
        )

        NoticeType.create(
            "rate_quote_no_results",
            "Contact request from rate-quote (no results)",
            "Contact request from rate-quote"
        )

        NoticeType.create(
            "contact_request_partner_page",
            "Contact request from partners page(customer)",
            "Contact request from partners page(customer)"
        )

        NoticeType.create(
            "admin_contact_request_landing",
            "Landing lead from thirdparty resource",
            "Landing lead"
        )

        NoticeType.create(
            "admin_contact_request_landing_extended",
            "Landing lead (extended) admin",
            "Landing lead (extended) admin"
        )

        NoticeType.create(
            "contact_request_landing_extended",
            "Landing lead (extended)",
            "Landing lead (extended)"
        )

        NoticeType.create(
            "administrative_contact_request_mobile",
            "Contact request from mobile chat",
            "Contact request from mobile chat"
        )

        NoticeType.create(
            "agent_prequalification",
            "Agent Notice of Prequalification",
            "Agent Notice of Prequalification"
        )
    else:
        print "Skipping creation of NoticeTypes in Contacts - notification app not found"


class ContactsConfig(AppConfig):
    name = 'contacts'
    verbose_name = "Contacts"

    def ready(self):
        signals.post_migrate.connect(create_notice_types, sender=self)
