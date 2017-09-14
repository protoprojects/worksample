from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns
import contacts.api_views

urlpatterns = format_suffix_patterns([
    url(r'^mortgage-profile/$', contacts.api_views.contact_request_mortgage_profile, name='mortgage_profile_list'),
    url(r'^consultation/$', contacts.api_views.contact_request_consultation, name='contact_request_consultation'),
    url(r'^about-us/$', contacts.api_views.contact_request_about_us, name='contact_request_about_us'),
    url(r'^partner/$', contacts.api_views.contact_request_partner, name='contact_request_partner'),
    url(r'^landing/$', contacts.api_views.contact_request_landing, name='contact_request_landing'),
    url(r'^landing-extended/$', contacts.api_views.contact_request_landing_extended,
        name='contact_request_landing_extended'),
    url(r'^mobile-profile/$', contacts.api_views.contact_request_mobile_profile, name='contact_request_mobile_profile'),
    url(r'^mobile-profile/(?P<pk>\d+)/$', contacts.api_views.contact_request_mobile_profile_detail,
        name='contact_request_mobile_profile_detail'),
    url(r'^unlicensed-state/$', contacts.api_views.contact_request_unlicensed_state_list,
        name='contact_request_unlicensed_state_list'),
    url(r'^mobile-profile/active/$', contacts.api_views.mobile_profile_active, name='mobile_profile_active'),
    url(r'^locations/counties/$', contacts.api_views.location_county_lookup, name='location_county_lookup'),
    url(r'^locations/(?P<zipcode>\d+)/$', contacts.api_views.location_zipcode_lookup, name='location_zipcode_lookup')
])
