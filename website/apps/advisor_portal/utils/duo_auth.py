from django.conf import settings

from rest_framework_jwt.settings import api_settings

import duo_web

jwt_decode_handler = api_settings.JWT_DECODE_HANDLER


def duo_authenticate(request, user_email):
    """
    Record in the session that the user has authenticated with Duo.
    """
    request.session['duo_authenticated'] = user_email


def duo_authenticated(request, user_email):
    """
    Return True if a session shows the user has authenticated with Duo.
    """
    return request.session.get('duo_authenticated') == user_email


def duo_check_login(request, user_email):
    if duo_authenticated(request, user_email):
        return True
    # To perform two-factor authentication,
    # need to store obtained JWT-token and email and
    # then return "401 Unauthorized" which means that
    # application need to redirect user to DUO login view.
    # Email will be used as user ID.
    request.session['duo_jwt_email'] = user_email
    return False


def duo_get_signature(request):
    stored_email = request.session.get('duo_jwt_email')
    if not stored_email:
        return None
    return duo_web.sign_request(
        settings.DUO_INTEGRATION_KEY,
        settings.DUO_SECRET,
        settings.SECRET_KEY,
        stored_email,
    )


def duo_perform_login(request):
    """
    Returns tuple - (is_authenticated, next)
    """
    sig_response = request.POST.get('sig_response', '')
    next_url = request.POST.get('next')
    duo_user = duo_web.verify_response(
        settings.DUO_INTEGRATION_KEY,
        settings.DUO_SECRET,
        settings.SECRET_KEY,
        sig_response
    )
    if duo_user is None:
        return False, None

    duo_authenticate(request, request.session['duo_jwt_email'])
    del request.session['duo_jwt_email']  # cleanup
    return True, next_url
