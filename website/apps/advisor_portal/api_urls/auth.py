from django.conf.urls import url
import advisor_portal.views.auth

urlpatterns = [
    url(r'^login/', advisor_portal.views.auth.advisor_portal_login_view, name='advisor_login'),
    url(r'^duo-login/', advisor_portal.views.auth.advisor_portal_login_duo_view, name='advisor_duo_login'),
    url(r'tokens-verify/', advisor_portal.views.auth.verify_token, name='verify_token')
]
