from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from advisor_portal.views.mixins import AdvisorTokenAuthMixin
from advisor_portal.permissions import AllowAdvisorPermission
from contacts.models import Location
from contacts.serializers import LocationSerializer
from core.models import EncompassSync


class LocationZipcodeLookup(AdvisorTokenAuthMixin,
                            viewsets.GenericViewSet,
                            viewsets.mixins.RetrieveModelMixin):
    permission_classes = (IsAuthenticated, AllowAdvisorPermission,)

    model = Location
    serializer_class = LocationSerializer
    lookup_field = "zipcode"
    queryset = Location.objects.all().cache()

location_zipcode_lookup = LocationZipcodeLookup.as_view({'get': 'retrieve'})


class LocationLookupView(AdvisorTokenAuthMixin,
                         viewsets.GenericViewSet,):
    permission_classes = (IsAuthenticated, AllowAdvisorPermission,)

    model = Location
    serializer_class = LocationSerializer
    queryset = Location.objects.all().cache()

    def list(self, request, *args, **kwargs):
        city = self.request.query_params.get('city')
        state = self.request.query_params.get('state')
        if not city or not state:
            return Response({'error': 'Both city and state are required.'}, status=400)
        city = city.replace('-', ' ')
        object_list = self.get_queryset().filter(city__icontains=city, state=state)
        if not object_list:
            return Response(status=404)
        return Response(self.get_serializer(object_list, many=True).data)

location_lookup = LocationLookupView.as_view({'get': 'list'})


class LosStatusView(AdvisorTokenAuthMixin, APIView):
    permission_classes = (IsAuthenticated, AllowAdvisorPermission,)

    def get(self, *args, **kwargs):
        data = {'status': 'enabled' if EncompassSync.enabled() else 'disabled'}
        return Response(data=data)

los_status_view = LosStatusView.as_view()
