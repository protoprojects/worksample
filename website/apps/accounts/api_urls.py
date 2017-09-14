from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns

import accounts.views

urlpatterns = format_suffix_patterns([
    url(r'^login/$', accounts.views.api_login_view, name="api-login"),
    url(r'^reset-password/$', accounts.views.api_reset_password_view, name="api-reset-password"),
    url(r'^update-password/$', accounts.views.api_update_password_view, name="api-update-password"),
    url(r'^change-password/(?P<token>[\w:-]+)/$', accounts.views.api_change_password_view, name="api-change-password"),
    url(r'^settings/$', accounts.views.api_customer_settings_view, name="api-customer-settings"),
    url(r'^subscription/$', accounts.views.api_customer_subscription_view, name="api-customer-subscription"),
    url(r'^verify-email/$', accounts.views.verify_email, name="api-verify-email"),
    url(r'^decline-email/$', accounts.views.decline_email, name="api-decline-email"),
    url(r'^(?P<customer_pk>\d+)/addresses/', accounts.views.api_customer_addresses, name='api-customer-addresses'),
    url(r'^phone-verification/twilio-callback/$', accounts.views.phone_verification_twilio_callback_view, name="api-phone-verification-twilio-callback"),
])
