from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns
import accounts.views

urlpatterns = format_suffix_patterns([
    url(r'^$', accounts.views.encompass_user_view, name="user"),
    url(r'^(?P<email>.+)/$', accounts.views.encompass_user_details, name="user_details"),
])
