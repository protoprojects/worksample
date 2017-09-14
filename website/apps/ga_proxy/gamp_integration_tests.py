'''
This is a file meant to be executed by hand to test the running
state of the ga_proxy REST endpoints.
'''
import json
from unittest import skipIf

from django.test import TestCase
import requests

import analytics

# Choose the right server to poke
# REST_END_POINT = "https://beta.sample.com/api/v1/ga-proxy/"
# REST_END_POINT = "https://www.sample.com/api/v1/ga-proxy/"
REST_END_POINT = "http://127.0.0.1:8000/api/v1/ga-proxy/"


def is_proxy_running():
    up = False
    try:
        sesh = requests.Session()
        sesh.get(REST_END_POINT)
        up = True
    except requests.exceptions.ConnectionError:
        up = False

    return up

PROXY_RUNNING = is_proxy_running()


def post_tag(endpoint="event", key_vals=None):
    '''
    Take given values and post a hit
    '''
    session = requests.Session()
    key_vals = key_vals
    url = REST_END_POINT + endpoint + '/'
    resp = session.post(url, data=json.dumps(key_vals))
    return resp


@skipIf(PROXY_RUNNING is False, "GA proxy not running")
class TestGaProxyMessages(TestCase):

    def test_simple_event(self):
        response = post_tag(endpoint="events",
                            key_vals={"ec": "easting",
                                      "ea": "examine",
                                      "cid": "XXX-XXX-YYY"})
        self.assertEqual(response.status_code, 201)

    def test_full_tags(self):
        response = post_tag(endpoint="tags",
                            key_vals={"t": "item",
                                      "v": "1",
                                      "tid": "UA-44728115-3",
                                      "dp": "foo",
                                      "cid": "abc",
                                      "td": "foo",
                                      "ti": "OD564",
                                      "in": "Mom",
                                      "iq": "1",
                                      "cu": "EUR"})
        self.assertEqual(response.status_code, 201)

    def test_pageview(self):
        response = post_tag(endpoint="pageviews",
                            key_vals={"dl": "easting", "ea": "examine", "cid": "FFF-DDD-EEEE"})
        self.assertEqual(response.status_code, 201)

    def test_malformed_event_type(self):
        response = post_tag(endpoint="events", key_vals=["cid", "XXX-XXX-YYY"])
        self.assertEqual(response.status_code, 400)

    def test_malformed_event_type_two(self):
        response = post_tag(endpoint="events", key_vals="cid: XXX-XXX-YYY")
        self.assertEqual(response.status_code, 400)


@skipIf(PROXY_RUNNING is False, "GA proxy not running")
class TestServerSideAnalyticsMessages(TestCase):

    def test_analytics_prequal_event(self):
        response = analytics.prequal_completed("ABC-DEF-GHI")
        self.assertTrue(response, "Event tag failed")
