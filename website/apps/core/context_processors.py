from urlparse import urlparse

from django.conf import settings


def base_url(request):
    """
    Return a BASE_URL template context for the current request.
    """
    scheme = 'https' if request.is_secure() else 'http'
    url = '{}://{}'.format(scheme, request.get_host())
    return {'BASE_URL': url}


def symantec_seal_url(request):
    site_path = getattr(settings, 'SITE_PATH', None)
    if not site_path:
        return ""

    o = urlparse(site_path)

    return {
        'SYMANTEC_SEAL_URL': "https://seal.websecurity.norton.com/getseal"
                             "?host_name={hostname}&size=S&use_flash=NO"
                             "&use_transparent=YES&lang=en".format(hostname=o.hostname)
    }


def main_phone_processor(request):
    return {'MAIN_PHONE_NUMBER': settings.MAIN_PHONE_NUMBER}


def main_email_processor(request):
    return {'MAIN_EMAIL_ADDRESS': settings.MAIN_EMAIL_ADDRESS}


def stage(request):
    return {
        'stage': settings.STAGE
    }


def dnt(request):
    http_dnt = request.META.get('HTTP_DNT')

    return {
        'is_DNT': http_dnt and http_dnt == '1'
    }
