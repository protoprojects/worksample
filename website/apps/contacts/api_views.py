import logging
import urllib

import mock

from django.conf import settings
from django.shortcuts import get_object_or_404

from pinax.notifications import models as notification
from rest_framework import generics, permissions, views, response, status

from core import utils as core_utils
from mortgage_profiles.models import MortgageProfile, RateQuoteLender
from mortgage_profiles.mortech import MortechFees
from core.utils import memoize
from referral.models import ContactRequestReferrer
from vendors.tasks import push_lead_to_salesforce


from contacts.models import (
    ContactRequestMortgageProfile, ConsultationRequest, NotificationReceiver, ContactRequestAboutUs,
    Location, ContactRequestPartner, ContactRequestLanding,
    ContactRequestLandingExtended, ContactRequestMobileProfile, ContactRequestUnlicensedState
)
from contacts.serializers import (
    ContactRequestMortgageProfileSerializer, ConsultationRequestSerializer, ContactRequestAboutUsSerializer,
    ContactRequestPartnerSerializer, LocationSerializer,
    ContactRequestLandingSerializer, ContactRequestLandingExtendedSerializer, ContactRequestMobileProfileSerializer,
    ContactRequestUnlicensedStateSerializer,
)
from contacts.permissions import IsMobileProfileOwner


logger = logging.getLogger("sample.contact_requests")


class NotificationMixin(object):
    ADMIN_LEAD_EMAIL = settings.ADMIN_BASE_LEAD_EMAIL
    NOTIFICATION_TO_ADVISOR_ENABLED = True

    @staticmethod
    def _get_mocked_user(obj):
        user = mock.MagicMock(
            email=obj.email,
            first_name=obj.first_name,
            last_name=obj.last_name,
            id=1,
        )
        return user

    @staticmethod
    def _get_mocked_recipient(email):
        """
        Temporary method for using `notification.send`
        Should be replaced with `Advisor` entity
        """
        user = mock.MagicMock(
            email=email,
            first_name=email,
            last_name=email,
            id=1,
        )
        return user

    def _pre_save(self, serializer):
        # pylint: disable=attribute-defined-outside-init
        if self.request.user.is_authenticated() and self.request.user.is_customer():
            self.object = serializer.save(user=self.request.user, session_id=self.request.user.account_number)
        else:
            self.object = serializer.save(session_id=self.request.session.get("account_number"))

    def _post_save(self):
        ContactRequestReferrer.objects.apply_referrer(self.object, self.request)
        self.send_administrative_notification()
        push_lead_to_salesforce.delay(self.object.id)

    def perform_create(self, serializer):
        self._pre_save(serializer)
        self._post_save()

    def send_administrative_notification(self):
        context = {"contact_request": self.object, 'lead_type': self.object.get_kind_display()}
        mortgage_profile_uuid = self.request.data.get('mortgage_profile_id')
        lender_id = self.request.data.get('lender_id')

        # if we have `mortgage_profile_uuid`, this is `ContactRequestMortgageProfileView`
        if mortgage_profile_uuid and lender_id:
            # Service switch stays for now so keep code as well. XXXkayhudson
            if settings.RATE_QUOTE_SERVICE == 'mortech':
                lender_class = RateQuoteLender
                calc_class = MortechFees
            lender = generics.get_object_or_404(lender_class, id=lender_id)
            mortgage_profile = generics.get_object_or_404(
                MortgageProfile.objects.select_subclasses(), uuid=mortgage_profile_uuid
            )
            context.update({
                'mortgage_profile': mortgage_profile,
                'lender': lender,
                'lender_calculations': calc_class(mortgage_profile, lender)
            })
        self.set_advisor()
        notification.send(
            self.get_administrative_notification_recipients(),
            self.ADMINISTRATIVE_NOTIFICATION_TYPE,
            context
        )

    @memoize
    def get_next_receiver(self):
        length = NotificationReceiver.objects.active().count()
        if length:
            return NotificationReceiver.objects.active()[self.object.id % length if length > 1 else 0]

    def set_advisor(self):
        if self.NOTIFICATION_TO_ADVISOR_ENABLED:
            receiver = self.get_next_receiver()
            if receiver:
                self.object.advisor = receiver
                self.object.save()

    def get_administrative_notification_recipients(self):
        recipients = [self._get_mocked_recipient(self.ADMIN_LEAD_EMAIL)]

        if self.NOTIFICATION_TO_ADVISOR_ENABLED:
            receiver = self.get_next_receiver()
            if receiver:
                recipients.append(self._get_mocked_recipient(receiver.email))

        return recipients

    def send_notification_to_existing_user(self, contact_request, user):
        pass

    def send_notification_to_new_user(self, contact_request, user, password):
        pass


class BaseContactRequestCreateView(NotificationMixin, generics.CreateAPIView):
    """
    Base class for contact request creating

    """

    def create(self, request, *args, **kwargs):
        resp = super(BaseContactRequestCreateView, self).create(request, *args, **kwargs)

        if resp.status_code == status.HTTP_201_CREATED:
            self.add_utm_info_if_exists()
        logger.debug('CONTACT-REQUEST-CREATE-MODEL %s', self.model)
        return resp

    def add_utm_info_if_exists(self):
        """
        Add existing "utm info" to contact request

        """

        utm_parameters_names = (
            'utm_source', 'utm_medium', 'utm_term', 'utm_content',
            'utm_campaign',
        )
        utm_info = {}

        for param_name in utm_parameters_names:
            value = self.request.GET.get(param_name)
            if value:
                utm_info[param_name] = value

        if utm_info:
            self.object.utm_info = urllib.urlencode(utm_info)
            self.object.save()


class ContactRequestMortgageProfileView(BaseContactRequestCreateView):
    ADMINISTRATIVE_NOTIFICATION_TYPE = 'administrative_contact_request'

    model = ContactRequestMortgageProfile
    serializer_class = ContactRequestMortgageProfileSerializer
    permission_classes = (permissions.AllowAny,)

    def perform_create(self, serializer):
        # pylint: disable=attribute-defined-outside-init
        mp = self.get_mortgage_profile()
        self.object = serializer.save(mortgage_profile=mp)
        logger.info('CONTACT-REQUEST-MORTGAGE-PROFILE-CREATED id %s', self.object.id)
        if not mp:
            logger.error('CONTACT-REQUEST-NO-MORTGAGE-PROFILE id %s', self.object.id)
        self._post_save()

    def get_mortgage_profile(self):
        mortgage_profile_uuid = self.request.session.get('mortgage_profile_uuid')
        core_utils.clear_session(self.request)
        if mortgage_profile_uuid:
            return generics.get_object_or_404(
                MortgageProfile.objects.select_subclasses(),
                uuid=mortgage_profile_uuid)
        else:
            return None

    def send_notification_to_existing_user(self, contact_request, user):
        # TODO
        pass

contact_request_mortgage_profile = ContactRequestMortgageProfileView.as_view()


class ContactRequestConsultationView(BaseContactRequestCreateView):
    ADMINISTRATIVE_NOTIFICATION_TYPE = 'administrative_inquiry'

    serializer_class = ConsultationRequestSerializer
    model = ConsultationRequest
    permission_classes = (permissions.AllowAny,)

    def send_notification_to_existing_user(self, contact_request, user):
        # TODO
        pass

    def send_notification_to_new_user(self, contact_request, user, password):
        notification.send([user], "inquiry_no_account", {
            "password": password,
            "contact_request": contact_request,
        })


contact_request_consultation = ContactRequestConsultationView.as_view()


class ContactRequestAboutUsView(BaseContactRequestCreateView):
    """
    Creates requests from About us page
    """

    ADMINISTRATIVE_NOTIFICATION_TYPE = 'administrative_contact_request_about_us'

    serializer_class = ContactRequestAboutUsSerializer
    model = ContactRequestAboutUs
    permission_classes = (permissions.AllowAny,)

    def send_notification_to_new_user(self, contact_request, user, password):
        notification.send([user], "inquiry_contact_us", {
            "password": password,
            "contact_request": contact_request,
        })

contact_request_about_us = ContactRequestAboutUsView.as_view()


class ContactRequestMobileProfileView(BaseContactRequestCreateView):
    """
    Creates requests from Mobile chats
    """
    ADMINISTRATIVE_NOTIFICATION_TYPE = 'administrative_contact_request_mobile'

    serializer_class = ContactRequestMobileProfileSerializer
    model = ContactRequestMobileProfile
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        resp = super(ContactRequestMobileProfileView, self).create(request, *args, **kwargs)
        if resp.status_code == status.HTTP_201_CREATED:
            self.add_utm_info_if_exists()
        request.session['mobile_profile_id'] = self.object.id
        return resp

contact_request_mobile_profile = ContactRequestMobileProfileView.as_view()


class ContactRequestMobileProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Gets or updates requests from Mobile chats
    """
    serializer_class = ContactRequestMobileProfileSerializer
    permission_classes = (IsMobileProfileOwner,)
    queryset = ContactRequestMobileProfile.objects.all()

contact_request_mobile_profile_detail = ContactRequestMobileProfileDetailView.as_view()


class ContactRequestUnlicensedStateListView(BaseContactRequestCreateView):
    """
    Creates requests from Mobile chats
    """
    serializer_class = ContactRequestUnlicensedStateSerializer
    model = ContactRequestUnlicensedState
    permission_classes = (permissions.AllowAny,)

    def _post_save(self):
        # this prevents sending a notification to anyone, or trying to create a salesforce lead
        pass

contact_request_unlicensed_state_list = ContactRequestUnlicensedStateListView.as_view()


class MobileProfileActiveRetrieveView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    # pylint: disable=no-self-use
    def get(self, request):
        """
        Return active mobile_profile_id if exists.
        """
        pk = request.session.get('mobile_profile_id')
        mobile_profile = get_object_or_404(ContactRequestMobileProfile, pk=pk)
        return response.Response({'id': mobile_profile.id})

mobile_profile_active = MobileProfileActiveRetrieveView.as_view()


class ContactRequestPartnerView(BaseContactRequestCreateView):
    """
    Creates request from landing page

    """
    ADMIN_LEAD_EMAIL = settings.ADMIN_PARTNERS_LEAD_EMAIL
    NOTIFICATION_TO_ADVISOR_ENABLED = False

    ADMINISTRATIVE_NOTIFICATION_TYPE = 'admin_contact_request_partner'

    serializer_class = ContactRequestPartnerSerializer
    model = ContactRequestPartner
    permission_classes = (permissions.AllowAny,)

    def send_notification_to_new_user(self, contact_request, user, password):
        notification.send([user], "contact_request_partner_page", {
            "contact_request": contact_request,
        })

contact_request_partner = ContactRequestPartnerView.as_view()


class ContactRequestLandingView(BaseContactRequestCreateView):
    ADMINISTRATIVE_NOTIFICATION_TYPE = 'admin_contact_request_landing'

    serializer_class = ContactRequestLandingSerializer
    model = ContactRequestLanding
    permission_classes = (permissions.AllowAny,)

contact_request_landing = ContactRequestLandingView.as_view()


class ContactRequestLandingExtendedView(BaseContactRequestCreateView):
    ADMINISTRATIVE_NOTIFICATION_TYPE = 'admin_contact_request_landing_extended'

    serializer_class = ContactRequestLandingExtendedSerializer
    model = ContactRequestLandingExtended
    permission_classes = (permissions.AllowAny,)

    def send_notification_to_new_user(self, contact_request, user, password):
        notification.send([user], "contact_request_landing_extended", {
            "contact_request": contact_request,
        })


contact_request_landing_extended = ContactRequestLandingExtendedView.as_view()


class LocationZipcodeLookup(generics.RetrieveAPIView):
    model = Location
    serializer_class = LocationSerializer
    lookup_field = "zipcode"
    queryset = Location.objects.all().cache()

location_zipcode_lookup = LocationZipcodeLookup.as_view()


class LocationCountyLookup(views.APIView):
    model = Location

    def get_queryset(self):
        state = self.request.query_params.get('state')

        if state:
            return Location.objects.filter(state=state).cache()
        return Location.objects.none()

    def get(self, request):
        qs = self.get_queryset()
        counties = [county
                    for county in qs.values_list("county", flat=True).distinct().order_by("county")
                    if county]
        return response.Response(counties)

location_county_lookup = LocationCountyLookup.as_view()
