from django import template
from django.conf import settings
from django.core import signing
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag
def get_contact_request_email_link(obj):
    return '%s%s' % (
        settings.SITE_PATH,
        reverse('contacts-generic:show-contact-request-email',
                args=[signing.dumps({'id': obj.id})]))
