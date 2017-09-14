from django import template
from django.conf import settings
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def absolute_uri(context, url_path):
    request = context.get('request')
    assert request, 'Request should be provided.'

    return request.build_absolute_uri(url_path)


@register.simple_tag()
def full_url(view_name, *args, **kwargs):
    return ''.join([settings.SITE_PATH, reverse(view_name, args=args, kwargs=kwargs)])


@register.simple_tag()
def get_blog_url_path():
    return settings.BLOG_URL_PATH


@register.filter
def keyvalue(dictionary, key):
    return dictionary.get(key)
