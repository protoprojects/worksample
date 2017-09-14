from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import ugettext

from pinax.notifications.backends.base import BaseBackend
from pinax.notifications.backends.email import EmailBackend

from core.tasks import send_message


class TemplateContextMixin(object):
    def get_context(self, recipient, sender, notice_type, extra_context):
        context = self.default_context()
        context.update({
            "static_path": settings.STATIC_URL,
            "recipient": recipient,
            "sender": sender,
            "notice": notice_type.display,
        })
        context.update(extra_context)
        return context


class MessageCenterBackend(BaseBackend, TemplateContextMixin):
    spam_sensitivity = 2

    MESSAGE_CENTER_LABELS = set(["contact_request_existing_user"])

    def can_send(self, user, notice_type, scoping):
        # FIXME: update when email for existing users will be implemented
        can_send = True
        # can_send = super(MessageCenterBackend, self).can_send(user, notice_type)
        return can_send and notice_type.label in self.MESSAGE_CENTER_LABELS

    def deliver(self, recipient, sender, notice_type, extra_context):
        # Runtime import is important to prevent the
        # issue with django migrations.
        from sample_notifications.models import Message

        context = self.get_context(recipient, sender, notice_type, extra_context)
        label = notice_type.label
        subject = render_to_string("pinax/notifications/%s/%s" % (label, "subject.txt"), context_instance=context)
        body = render_to_string("pinax/notifications/%s/%s" % (label, "body.html"), context_instance=context)
        message = Message(label=label, user=recipient, content=body, subject=subject)
        message.save()


class SesAsyncEmailBackend(EmailBackend, TemplateContextMixin):
    spam_sensitivity = 2

    def can_send(self, user, notice_type, scoping):
        can_send = super(SesAsyncEmailBackend, self).can_send(user, notice_type, scoping)
        if can_send and user.email:
            return True
        return False

    def deliver(self, recipient, sender, notice_type, extra_context):
        attachments = extra_context.pop('attachments', [])

        context = self.default_context()
        context.update({
            "recipient": recipient,
            "sender": sender,
            "notice": ugettext(notice_type.display),
        })
        context.update(extra_context)

        messages = self.get_formatted_messages((
            "subject.txt",
            "body.txt",
            "body.html",
        ), notice_type.label, context)

        msg = EmailMultiAlternatives(
            subject=messages["subject.txt"].strip(),
            body=messages["body.txt"],
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email]
        )
        msg.attach_alternative(messages["body.html"], "text/html")

        if attachments:
            for attachment in attachments:
                msg.attach(attachment['name'], attachment['data'], attachment['content_type'])

        send_message.delay(msg, notice_type.label)
