import logging

from django.http import HttpResponseNotFound
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from accounts.serializers import UserProfileSerializer
from accounts.views import UserProfileView

from advisor_portal.permissions import AllowAdvisorPermission
from advisor_portal.serializers.advisor import AdvisorCustomerSerializer
from advisor_portal.views.mixins import AdvisorSetMixin, AdvisorTokenAuthMixin

logger = logging.getLogger('advisor_portal.views.advisor')


class AdvisorProfileView(UserProfileView):
    """
    Retrieve advisor profile.

    """
    permission_classes = (IsAuthenticated, AllowAdvisorPermission,)
    serializer_class = UserProfileSerializer

advisor_profile_view = AdvisorProfileView.as_view()


class AdvisorCustomerView(AdvisorTokenAuthMixin,
                          AdvisorSetMixin,
                          viewsets.GenericViewSet,
                          viewsets.mixins.CreateModelMixin,
                          viewsets.mixins.RetrieveModelMixin):

    permission_classes = (IsAuthenticated, AllowAdvisorPermission,)
    serializer_class = AdvisorCustomerSerializer

    def get_queryset(self):
        return self.request.user.customer_set.all()

advisor_customer_create_view = AdvisorCustomerView.as_view({'post': 'create'})
advisor_customer_view = AdvisorCustomerView.as_view({'get': 'retrieve'})


class AdvisorLoanProfileGuidIdView(AdvisorTokenAuthMixin, APIView):
    """Map Loan Profile GUID to (database) Id"""

    permission_classes = (IsAuthenticated, AllowAdvisorPermission,)

    def get_queryset(self):
        guid = self.kwargs['guid']
        return self.request.user.loan_profilesV1.filter(guid=guid)

    def get(self, *args, **kwargs):
        loan_profiles = self.get_queryset()
        loan_profile = loan_profiles[0] if loan_profiles else None
        if loan_profile:
            # We could use a redirect here, but safari does not resend jwt auth
            data = {'id': loan_profile.id}
            retval = Response(data=data)
        else:
            retval = HttpResponseNotFound(
                'GUID not found: {}'.format(self.kwargs['guid']))
        return retval

advisor_loan_profile_guid_id_view = AdvisorLoanProfileGuidIdView.as_view()
