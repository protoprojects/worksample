from django.conf.urls import url

from box import callback_views

urlpatterns = [
    url(r'^selfoauth/$', callback_views.oauth_self, name='self_oauth'),
    url(r'^redirect/self/$', callback_views.oauth_redirect_url_self, name='box_redirect_url_self'),
]
