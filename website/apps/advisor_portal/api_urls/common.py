from django.conf.urls import url
import advisor_portal.views.common

urlpatterns = [
    url(r'^zipcode-lookup/(?P<zipcode>[0-9]+)/$', advisor_portal.views.common.location_zipcode_lookup,
        name='zipcode_lookup'),
    url(r'^location-lookup/$', advisor_portal.views.common.location_lookup, name='location_lookup'),
    url(r'^los-status/$', advisor_portal.views.common.los_status_view, name='los_status_view'),
]
