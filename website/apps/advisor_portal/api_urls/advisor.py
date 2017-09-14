from django.conf.urls import url

from core.regex import UUID4_REGEX
import advisor_portal.views.advisor

urlpatterns = [
    url(r'^advisor/$', advisor_portal.views.advisor.advisor_profile_view, name='advisor_profile_view'),

    url(r'^advisor/customers/$',
        advisor_portal.views.advisor.advisor_customer_create_view,
        name='advisor_customer_create_view'),

    url(r'^advisor/customers/(?P<pk>[0-9]+)/$',
        advisor_portal.views.advisor.advisor_customer_view,
        name='advisor_customer_view'),

    url(r'^advisor/guid/(?P<guid>%s)/$' % UUID4_REGEX,
        advisor_portal.views.advisor.advisor_loan_profile_guid_id_view,
        name='advisor_loan_profile_guid_id_view'),
]
