import json
import logging

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.views import JSONWebTokenLoginView, VerifyJSONWebTokenView

from advisor_portal.serializers.auth import AdvisorJSONWebTokenSerializer
from advisor_portal.utils.duo_auth import (
    duo_check_login, duo_get_signature, duo_perform_login
)

logger = logging.getLogger('advisor_portal.views.auth')


class AdvisorPortalLoginView(JSONWebTokenLoginView):
    """
    Advisor Portal Login API View.

    Returns a JSON Web Token, if DUO is disabled
    or user if already authenticated via DUO.
    In the other case it will return client error.
    """
    throttle_scope = settings.REST_FRAMEWORK_ADVISOR_PORTAL_THROTTLE
    serializer_class = AdvisorJSONWebTokenSerializer

    @classmethod
    def update_last_login(cls, user_email):
        users = User.objects.filter(email=user_email)
        if users:
            try:
                for user in users:
                    update_last_login(None, user)
            except Exception:
                # ALIBI: allowing login for read-only, but logging cause
                logger.exception('ADVISOR-JWT-LAST-LOGIN-FAILED-TO-UPDATE')
            return True
        return False

    def post(self, request):
        # JWT part
        jwt_response = super(AdvisorPortalLoginView, self).post(request)

        if jwt_response.status_code == status.HTTP_400_BAD_REQUEST:
            return jwt_response

        # DUO part
        user_email = request.data['username']

        if not settings.ADVISOR_PORTAL_DUO_AUTH_ENABLED:
            if AdvisorPortalLoginView.update_last_login(user_email):
                return jwt_response
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        is_authenticated_with_duo = duo_check_login(request, user_email)
        if not is_authenticated_with_duo:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        if AdvisorPortalLoginView.update_last_login(user_email):
            return jwt_response
        return Response(status=status.HTTP_401_UNAUTHORIZED)

advisor_portal_login_view = AdvisorPortalLoginView.as_view()


class AdvisorVerifyTokenView(VerifyJSONWebTokenView):
    throttle_scope = settings.REST_FRAMEWORK_ADVISOR_PORTAL_THROTTLE

verify_token = AdvisorVerifyTokenView.as_view()


class AdvisorPortalDUOLoginView(APIView):
    """
    Advisor Portal DUO Login View.

    GET  : Returns needed credentials to perform DUO authentication
    POST : Performs authentication
    """
    permission_classes = (permissions.AllowAny,)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(AdvisorPortalDUOLoginView, self).dispatch(request, *args, **kwargs)

    # pylint: disable=no-self-use
    def get(self, request):
        if not settings.ADVISOR_PORTAL_DUO_AUTH_ENABLED:
            return HttpResponse(
                status=status.HTTP_403_FORBIDDEN,
            )

        duo_signature = duo_get_signature(request)
        if not duo_signature:
            return HttpResponse(
                status=status.HTTP_403_FORBIDDEN,
            )
        data = {
            'duo_signature': duo_signature,
            'duo_host': settings.ADVISOR_PORTAL_DUO_API_HOST,
        }
        return HttpResponse(
            status=status.HTTP_200_OK,
            content=json.dumps(data),
            content_type='application/json'
        )

    # pylint: disable=no-self-use
    def post(self, request):
        if not settings.ADVISOR_PORTAL_DUO_AUTH_ENABLED:
            return HttpResponse(
                status=status.HTTP_403_FORBIDDEN,
            )

        is_authenticated, next_url = duo_perform_login(request)
        if not is_authenticated:
            return HttpResponse(
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return HttpResponseRedirect(next_url)

advisor_portal_login_duo_view = AdvisorPortalDUOLoginView.as_view()
