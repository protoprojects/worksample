import logging
from django.conf import settings
from requests_futures.sessions import FuturesSession

GAMP_URL = 'http://www.google-analytics.com/collect'
GAMP_VALIDATING_URL = 'http://www.google-analytics.com/debug/collect'
logger = logging.getLogger('ga-proxy-logger')

PROXY_MODE_ENABLE = "ENABLE"
PROXY_MODE_DEBUG = "DEBUG"
PROXY_MODE_OFF = "OFF"
_proxy_mode = getattr(settings, 'GA_PROXY_MODE', PROXY_MODE_OFF)


def send(payload):
    '''
    payload - a dict of values to send
    no return value
    '''
    if _proxy_mode == PROXY_MODE_ENABLE:
        _send_immediate(payload)
    elif _proxy_mode == PROXY_MODE_DEBUG:
        send_validate(payload)


def send_validate(payload):
    '''
    Take care using this in production, it will block web threads.

    payload - a dict of values to send

    Send a GA message and wait for the response.
    Return the response object (r.content and r.status_code are interesting)
    Content should be GA's parsing of the message
    '''
    logger.info('GA-PROXY-VALIDATION-PAYLOAD payload ' + unicode(payload))
    resp = _send_immediate(
        payload, wait_for_response=True, destination=GAMP_VALIDATING_URL)
    logger.info('GA-PROXY-VALIDATION-RESPONSE response ' + unicode(resp.content))

    return resp


def _send_immediate(payload, wait_for_response=False, destination=GAMP_URL):
    '''
    payload - a dict of values to send
    wait_for_response - boolean - should we wait for and return a response
    desintation - a url, the analytics end point

    Send POST immeidately
    all network activity occurs in the background unless waited for
    '''
    session = FuturesSession()
    future = session.post(destination, params=payload)
    if wait_for_response:
        return future.result()


if __name__ == "__main__":
    # pylint: disable=wrong-import-order,wrong-import-position
    from pprint import pprint
    r = _send_immediate({"test": "pass", "exam": "retake"},
                        wait_for_response=True, destination=GAMP_VALIDATING_URL)
    pprint(r.content)
    pprint(r.status_code)
