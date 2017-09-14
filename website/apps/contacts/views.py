from django.conf import settings
from django.core import signing
from django.http import HttpResponse
from django.shortcuts import render
from django.template.context import RequestContext
from django.views.generic import View

from accounts.models import Customer

from contacts import models


class ShowContactRequestEmailView(View):
    TEMPLATES_MAPPING = {
        'ContactRequestAboutUs': 'pinax/notifications/inquiry_contact_us/body.html',
        'ContactRequestLandingExtended':
            'pinax/notifications/contact_request_landing_extended/body.html',
        'ContactRequestMortgageProfile': 'pinax/notifications/rate_quote_no_results/body.html',
        'ConsultationRequest': 'pinax/notifications/inquiry_no_account/body.html',
    }

    def _get_response(self, request, obj):
        try:
            context = RequestContext(request)
            context.update({
                'static_path': settings.STATIC_URL,
                'contact_request': obj,
                'recipient': Customer(email=obj.email,
                                      first_name=obj.first_name,
                                      last_name=obj.last_name)
            })

            return render(
                request,
                self.TEMPLATES_MAPPING[obj.__class__.__name__],
                context=context.flatten()
            )
        except KeyError:
            return HttpResponse(status=404)

    def get(self, request, email_hash):
        try:
            payload = signing.loads(email_hash)
        except signing.BadSignature:
            return HttpResponse(status=404)
        try:
            contact_request_obj = models.ContactRequest.objects.select_subclasses().get(
                id=payload['id'])
        except models.ContactRequest.DoesNotExist:
            return HttpResponse(status=404)
        return self._get_response(request, contact_request_obj)
