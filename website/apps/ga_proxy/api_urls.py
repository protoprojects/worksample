from django.conf.urls import url
from ga_proxy import views

urlpatterns = [
    url(r'^tags/', views.GoogleAnalyticsTagView.as_view(), name='ga-tags'),
    url(r'^events/', views.GoogleAnalyticsEventView.as_view(), name='ga-events'),
    url(r'^pageviews/', views.GoogleAnalyticsPageviewView.as_view(), name='ga-pageviews'),
]
