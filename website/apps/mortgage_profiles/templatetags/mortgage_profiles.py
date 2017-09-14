from django.contrib.humanize.templatetags.humanize import intcomma
from django import template

register = template.Library()

AMORTIZATION_TYPE_MAPPING = {
    "Fixed": "Fixed",
    "ARM": "Adjustable"
}


@register.filter
def currency(value):
    try:
        return "${}".format(intcomma(int(value)))
    except (ValueError, TypeError):
        pass


@register.filter
def humanize_amortization_type(amortization_type):
    return AMORTIZATION_TYPE_MAPPING.get(amortization_type)
