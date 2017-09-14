from django.conf.urls import url

from health_check import api_views


urlpatterns = [
    url(r'^$', api_views.index, name='index'),
]
