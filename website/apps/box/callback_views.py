import logging

from boxsdk.auth.oauth2 import OAuth2
from boxsdk.exception import BoxException
from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseServerError
from django.views.generic import View

from .utils import store_tokens_callback


BOX_API_OAUTH_STATE_SESSION_NAME = 'box_oauth_state'

logger = logging.getLogger('sample.box.callbacks')


class OAuthSelf(View):
    """
    Generate OAuth authorization URL and redirect to Box to manage application permissions.
    """

    # pylint: disable=R0201
    def get(self, request):
        # TODO need review. Asana #287939142987747
        oauth = OAuth2(settings.BOX_API_OAUTH_CLIENT_ID,
                       settings.BOX_API_OAUTH_CLIENT_SECRET)
        auth_url, oauth_state = oauth.get_authorization_url(settings.BOX_API_OAUTH_REDIRECT_URL_SELF)
        request.session[BOX_API_OAUTH_STATE_SESSION_NAME] = oauth_state
        return HttpResponseRedirect(auth_url)

oauth_self = OAuthSelf.as_view()


class OAuthRedirectUrlSelf(View):
    """
    Request OAuth access token credentials per received authorization code from Box.
    """

    # pylint: disable=R0201
    def get(self, request):
        oauth_state = request.session[BOX_API_OAUTH_STATE_SESSION_NAME]
        request_state = request.GET.get('state', None)
        if (oauth_state == request_state) and (oauth_state is not None):
            request_code = request.GET.get('code', None)
            # TODO need review. Asana #287939142987747
            oauth = OAuth2(settings.BOX_API_OAUTH_CLIENT_ID,
                           settings.BOX_API_OAUTH_CLIENT_SECRET,
                           store_tokens=store_tokens_callback)
            try:
                _, refresh_token = oauth.authenticate(request_code)
            except BoxException as exc:
                # !!! Early return
                logger.error('BOX-OAUTH-REDIRECT-URL-SELF-AUTHENTICATE-EXCEPTION %s', exc)
                return HttpResponseServerError('OAuth failure')
            logger.debug('BOX-OAUTH-REDIRECT-URL-SELF-SUCCESS')
            response = HttpResponse('congratulations {}'.format(refresh_token),
                                    content_type='text/plain')
        else:
            logger.error(
                'BOX-OAUTH-REDIRECT-URL-SELF-STATE-MISMATCH oauth-state %s request-state %s',
                oauth_state,
                request_state)
            # pylint: disable=redefined-variable-type
            response = HttpResponseServerError('OAuth failure')
        return response

oauth_redirect_url_self = OAuthRedirectUrlSelf.as_view()
