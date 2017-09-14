import logging

from django.conf import settings

import fasteners
from boxsdk.client import Client
from boxsdk.auth import CooperativelyManagedOAuth2


logger = logging.getLogger('sample.box.utils')


_client = None
rw_lock = fasteners.ReaderWriterLock()


def store_tokens_callback(access_token, refresh_token):
    """
    Callback accept tokens and storing them.

    :param access_token:
        Access token to use for auth until it expires.
    :type access_token:
        `unicode`
    :param refresh_token:
        Refresh token to use for auth until it expires or is used.
    :type refresh_token:
        `unicode`
    :returns: None
    """
    with rw_lock.write_lock():
        with open(settings.BOX_API_OAUTH_TOKEN_STORE, 'w') as f:
            f.write('{}\n{}\n'.format(access_token, refresh_token))


def retrieve_tokens_callback():
    """
    Callback to get the current access and refresh tokens.

    :returns: Tuple containing the current access token and refresh token.
    :rtype: `tuple` of ((`unicode` or `None`), (`unicode` or `None`))
    """
    with rw_lock.read_lock():
        with file(settings.BOX_API_OAUTH_TOKEN_STORE) as f:
            access = f.readline().strip()
            refresh = f.readline().strip()
        return (access, refresh)


# Who loves singletons?
def box_client_factory():
    # pylint: disable=W0603, protected-access
    global _client
    _access_token, _refresh_token = retrieve_tokens_callback()
    if _client is None:
        oauth = CooperativelyManagedOAuth2(
            client_id=settings.BOX_API_OAUTH_CLIENT_ID,
            client_secret=settings.BOX_API_OAUTH_CLIENT_SECRET,
            access_token=_access_token,
            refresh_token=_refresh_token,
            store_tokens=store_tokens_callback,
            retrieve_tokens=retrieve_tokens_callback
        )
        _client = Client(oauth)
        logger.debug('BOX-UTILS-CLIENT-INSTANTIATED')
    else:
        _client._oauth._access_token, _client._oauth._refresh_token = (_access_token, _refresh_token)
    return _client


def auth_exercise():
    """
    An lightweight-ish auth operation which does not hit the db
    """
    box_client_factory().events().get_events(limit=10)
