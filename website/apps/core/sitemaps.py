# -*- coding: utf-8 -*-

from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse


class GeneralSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return [
            'index',
            'page-about-us',
            'page-our-team',
            'page-careers',
            'apply',
            'our-process',
            'faq',
            'pros',
            'partners',
            'privacy-security',
            'terms-of-use'
        ]

    def location(self, item):
        return reverse(item)
