# coding: utf-8
# pylint: disable=protected-access

import os

import mock
import fasteners

from rest_framework import status
from urlparse import urlparse, parse_qs
from urllib import urlencode
from boxsdk.auth import CooperativelyManagedOAuth2

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

from box.utils import retrieve_tokens_callback, store_tokens_callback
from core.utils import LogMutingTestMixinBase


class BoxRefreshMutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.box.utils']


class BoxSettingsMixin(object):
    def setUp(self):
        super(BoxSettingsMixin, self).setUp()
        self.client_id = 'fake-client-id'
        self.client_secret = 'fake-client-secret'
        self.access_token = 'fake-access-token'
        self.refresh_token = 'fake-refresh-token'
        self.token_store = '/tmp/fake-box-tokens'
        settings_patcher = mock.patch(
            'box.utils.settings',
            BOX_API_OAUTH_CLIENT_ID=self.client_id,
            BOX_API_OAUTH_CLIENT_SECRET=self.client_secret,
            BOX_API_OAUTH_TOKEN_STORE=self.token_store)
        settings_patcher.start()
        if os.access(self.token_store, os.R_OK):
            os.remove(self.token_store)
        self.addCleanup(settings_patcher.stop)
        self.addCleanup(lambda: os.access(self.token_store, os.W_OK) and
                        os.remove(self.token_store))
        self.addCleanup(lambda: os.access(self.token_store + '.lock', os.W_OK) and
                        os.remove(self.token_store + '.lock'))


class BoxRefreshStoreLoad(BoxRefreshMutingMixin, BoxSettingsMixin, TestCase):
    def test_store_load(self):
        store_tokens_callback(self.access_token, self.refresh_token)
        access, refresh = retrieve_tokens_callback()
        self.assertEqual(self.access_token, access)
        self.assertEqual(self.refresh_token, refresh)


class BoxRefreshTest(BoxRefreshMutingMixin, BoxSettingsMixin, TestCase):
    def setUp(self):
        super(BoxRefreshTest, self).setUp()
        network_response = mock.Mock(json=mock.Mock(), ok=True)
        network_layer = mock.Mock(request=mock.Mock(return_value=network_response))
        rw_lock = fasteners.ReaderWriterLock()
        oauth = CooperativelyManagedOAuth2(
            client_id=self.client_id,
            client_secret=self.client_secret,
            store_tokens=store_tokens_callback,
            retrieve_tokens=retrieve_tokens_callback,
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            network_layer=network_layer)
        self.oauth = oauth
        self.addCleanup(lambda: os.access(self.token_store, os.W_OK) and
                        os.remove(self.token_store))

    def test_refresh_same_access_loads_new(self):
        different_access_token = 'different-access-token'
        different_refresh_token = 'different-refresh-token'
        tokens_dict = dict(
            access_token=different_access_token,
            refresh_token=different_refresh_token)
        self.oauth._network_layer.request.return_value.json.return_value = tokens_dict
        store_tokens_callback(self.access_token, self.refresh_token)
        result = self.oauth.refresh(self.access_token)
        self.assertTrue(self.oauth._network_layer.request.called)
        self.assertEqual(different_access_token, result[0])
        self.assertEqual(different_refresh_token, result[1])
        self.assertEqual(different_access_token, self.oauth._access_token)
        self.assertEqual(different_refresh_token, self.oauth._refresh_token)

    def test_refresh_different_access_does_nothing(self):
        different_access_token = 'different-access-token'
        different_refresh_token = 'different-refresh-token'
        tokens_dict = dict(
            access_token=different_access_token,
            refresh_token=different_refresh_token)
        self.oauth._network_layer.request.return_value.json.return_value = tokens_dict
        store_tokens_callback(self.access_token, self.refresh_token)
        result = self.oauth.refresh(different_access_token)
        self.assertFalse(self.oauth._network_layer.request.called)
        self.assertEqual(self.access_token, result[0])
        self.assertEqual(self.refresh_token, result[1])
        self.assertEqual(self.access_token, self.oauth._access_token)
        self.assertEqual(self.refresh_token, self.oauth._refresh_token)

    def test_refresh_same_unable_to_retrieve_tokens(self):
        different_access_token = 'different-access-token'
        different_refresh_token = 'different-refresh-token'
        tokens_dict = dict(
            access_token=different_access_token,
            refresh_token=different_refresh_token)
        self.oauth._network_layer.request.return_value.json.return_value = tokens_dict
        # different tokens in file which do not get loaded in this test
        store_tokens_callback(different_access_token, different_refresh_token)
        self.assertFalse(self.oauth._network_layer.request.called)
        self.assertEqual(self.access_token, self.oauth._access_token)
        self.assertEqual(self.refresh_token, self.oauth._refresh_token)


class TestOAuthSelf(BoxRefreshMutingMixin, BoxSettingsMixin, TestCase):
    def get_redirect_url(self):
        url = reverse('self_oauth')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        return response.url

    def test_get_authorization_url(self):
        redirect_url = self.get_redirect_url()
        parse_url = urlparse(redirect_url)
        query = parse_qs(parse_url.query)
        redirect_url = query.get('redirect_uri')[0]
        self.assertEqual(redirect_url, settings.BOX_API_OAUTH_REDIRECT_URL_SELF)

    @mock.patch('boxsdk.auth.oauth2.OAuth2.authenticate')
    def test_success_request_access_token_credentials(self, mocked_box_authenticate):
        mocked_box_authenticate.return_value = (self.access_token, self.refresh_token)
        redirect_url = self.get_redirect_url()
        parse_url = urlparse(redirect_url)
        query = parse_qs(parse_url.query)
        query_dict = dict(state=query['state'][0], code=self.access_token)
        url = query.get('redirect_uri')[0] + '?' + urlencode(query_dict)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, 'congratulations {}'.format(self.refresh_token))

    @mock.patch('boxsdk.auth.oauth2.OAuth2.authenticate')
    def test_fail_request_access_token_credentials(self, mocked_box_authenticate):
        mocked_box_authenticate.return_value = (self.access_token, self.refresh_token)
        redirect_url = self.get_redirect_url()
        parse_url = urlparse(redirect_url)
        query = parse_qs(parse_url.query)
        query_dict = dict(state='no-exists-state', code='no-exists-code')
        url = query.get('redirect_uri')[0] + '?' + urlencode(query_dict)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


