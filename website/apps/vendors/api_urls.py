from django.conf.urls import url
import vendors.views

urlpatterns = [
    url(r'^sf/loan-profiles/$', vendors.views.vendor_salesforce_create_view, name='vendor_salesforce_create_view'),
]
