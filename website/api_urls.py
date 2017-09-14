from django.conf.urls import url, include

urlpatterns = [
    # sample API urls
    url(r'^contact-requests/', include('contacts.api_urls', namespace="contact_requests")),
    url(r'^mortgage-profiles/', include('mortgage_profiles.api_urls', namespace="mortgage_profiles")),
    url(r'^accounts/', include('accounts.api_urls', namespace="accounts")),
    url(r'^notifications/', include('sample_notifications.api_urls', namespace='notifications')),
    url(r'^chat/', include('chat.api_urls', namespace='chat')),

    # Encompass API urls
    url(r'^encompass/', include('encompass_urls')),

    # Advisor portal urls
    url(r'^advisor-portal/', include('advisor_portal.urls', namespace='advisor-portal')),

    # Customer portal urls
    url(r'^cp/', include('customer_portal.urls', namespace='cp')),

    # Loan Expert
    url(r'^affordability/', include('affordability.api_urls', namespace='affordability')),

    # AWS ELB health check
    url(r'^health-check/', include('health_check.api_urls', namespace='health-check')),

    # Google Analytics Proxy
    url(r'^ga-proxy/', include('ga_proxy.api_urls', namespace='ga-proxy')),

    # Independent Credit Pull urls
    url(r'^credit/', include('mismo_credit.api_urls', namespace='mismo_credit')),

    # Vendor urls
    url(r'^vendor/', include('vendors.api_urls', namespace='vendors')),
]
