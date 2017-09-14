from django.conf.urls import url, include

import accounts.views

urlpatterns = [
    url(r'^settings/$', accounts.views.customer_settings_view, name="user_settings"),
    url(r'^login/$', accounts.views.login_view, name='login'),
    url(r'^logout/$', accounts.views.logout, name='logout'),
    url(r'^registration/$', accounts.views.registration_view, name="registration"),
    url(r'^password_change/$', accounts.views.password_change, name='password_change'),
    url(r'^reset-password/(?P<token>[\w:-]+)/$', accounts.views.reset_password_done_view, name="reset-password-done"),
    url(r'^', include('authtools.urls')),
]
