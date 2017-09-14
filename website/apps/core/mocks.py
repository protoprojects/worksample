import requests
from httmock import urlmatch, remember_called


@urlmatch(scheme='https', netloc='www.google.com', path='/recaptcha/api/siteverify', method='post')
@remember_called
def recapcha_response_timeout(url, request):
    raise requests.exceptions.Timeout
