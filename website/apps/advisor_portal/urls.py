from django.conf.urls import include, url


urlpatterns = [
    url(r'^', include('advisor_portal.api_urls.auth')),
    url(r'^', include('advisor_portal.api_urls.advisor')),
    url(r'^', include('advisor_portal.api_urls.common')),
    url(r'^', include('advisor_portal.api_urls.loan_profile_v1')),
]
