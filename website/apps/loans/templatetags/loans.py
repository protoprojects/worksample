from datetime import datetime

from django import template

register = template.Library()


@register.filter
def strptime(text, date_format):
    try:
        return datetime.strptime(text, date_format)
    except ValueError:
        return text
