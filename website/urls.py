from django.contrib import admin
from django.conf import settings
from django.conf.urls import include, url
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView, RedirectView
import django.views.static

from core import sitemaps
from core.views import EmailTestingView
from pages import views

admin.autodiscover()

urlpatterns = [
    # 3rd
    url(r'^admin/', include(admin.site.urls)),

    # website
    url(r'^$', views.IndexView.as_view(), name="index"),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^contacts/', include('contacts.urls', namespace='contacts-generic')),
    url(r'^learn/', RedirectView.as_view(url=settings.BLOG_URL_PATH, permanent=True)),

    # landing pages
    url(r'^landing-contact-request/(?P<anything>.*)$',
        RedirectView.as_view(url=settings.SITE_PATH, permanent=True)),
    url(r'^save(\/(step[123]|thanks)?)?$', RedirectView.as_view(url=settings.SITE_PATH, permanent=True)),
    url(r'^two-step(\/(form|thanks)?)?$', RedirectView.as_view(url=settings.SITE_PATH, permanent=True)),

    # utils
    url(r'^box/', include('box.urls')),
    url(r'^sitemap\.xml$', sitemap,
        {'sitemaps': {'general': sitemaps.GeneralSitemap}}),

    # api
    url(r'^api/v1/', include('api_urls')),

    # callbacks
    url(r'^callbacks/box/', include('box.callback_urls')),
]


if settings.DEBUG:
    urlpatterns += [
        # Test emails rendering
        url(r'^email/$',
            TemplateView.as_view(template_name="pinax/notifications/introducing-email.html"),
            name="email"),
        url(r'^email/(?P<email>.*)/$',
            EmailTestingView.as_view(template="pinax/notifications/introducing-email.html"),
            name="send-email"),
        url(r'^404/$', TemplateView.as_view(template_name="404.html"), name="404"),

        url(r"%s(?P<path>.*)$" % settings.STATIC_URL[1:], django.views.static.serve, {
            "document_root": settings.STATIC_ROOT,
            'show_indexes': True,
        }),
        url(r"%s(?P<path>.*)$" % settings.MEDIA_URL[1:], django.views.static.serve, {
            "document_root": settings.MEDIA_ROOT,
            'show_indexes': True,
        }),
    ]

if not settings.REST_FRAMEWORK_DOCS.get('HIDE_DOCS', True):
    urlpatterns += [
        url(r'^docs/', include('rest_framework_docs.urls')),
    ]
