from django.conf import settings
from django.core import signing
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.template.context import RequestContext
from django.test import TestCase
from django.utils.encoding import smart_text

from contacts import factories, models as contacts_models


class TestShowContactRequestEmailView(TestCase):
    def _get_email_content(self, obj):
        return self.client.get(
            reverse('contacts-generic:show-contact-request-email',
                    args=[signing.dumps({'id': obj.id})])
        )

    def assertContentEqual(self, response, obj, template):
        user = contacts_models.Customer(
            email=obj.email,
            first_name=obj.first_name,
            last_name=obj.last_name
        )
        context = RequestContext(response.context['request'])
        context.update({
            "static_path": settings.STATIC_URL
        })
        self.assertEqual(render_to_string('pinax/notifications/%s/body.html' % template,
                                          {'contact_request': obj,
                                           'recipient': user}),
                         smart_text(response.content))

    def test_get_contact_request_about_us(self):
        obj = factories.ContactRequestAboutUsFactory()
        response = self._get_email_content(obj)
        self.assertContentEqual(response, obj, 'inquiry_contact_us')

    def test_get_contact_request_landing_extended(self):
        obj = factories.ContactRequestLandingExtendedFactory()
        response = self._get_email_content(obj)
        self.assertContentEqual(response, obj, 'contact_request_landing_extended')

    def test_get_contact_request_mortgage_profile(self):
        obj = factories.ContactRequestMortgageProfileFactory()
        response = self._get_email_content(obj)
        self.assertContentEqual(response, obj, 'rate_quote_no_results')

    def test_get_consultation_request(self):
        obj = factories.ConsultationRequestFactory()
        response = self._get_email_content(obj)
        self.assertContentEqual(response, obj, 'inquiry_no_account')
