from django.conf.urls import url

from contacts.views import ShowContactRequestEmailView


urlpatterns = [
    url(r'^show-email/(?P<email_hash>[a-zA-Z0-9:_-]+)/$',
        ShowContactRequestEmailView.as_view(),
        name='show-contact-request-email')
]
