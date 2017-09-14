"""
Module is copied from https://github.com/duosecurity/duo_python/blob/master/demos/django/duo_app/duo_auth.py
With small additions and fixes

"""

from functools import wraps
import urllib

from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.template import RequestContext, loader
from django.templatetags.static import static
from django.views.decorators.http import require_http_methods
from django.utils.decorators import available_attrs
from django.contrib.auth.decorators import login_required
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.http import urlquote

import duo_web


def duo_username(user):
    """ Return the Duo username for user. """
    return user.email


def duo_authenticated(request):
    """
    Return True if a session shows the user has authenticated with Duo.
    """
    return request.session.get('duo_authenticated') == duo_username(request.user)


def duo_authenticate(request):
    """
    Record in the session that the user has authenticated with Duo.
    """
    request.session['duo_authenticated'] = duo_username(request.user)


def duo_unauthenticate(request):
    """
    Record in the session that the user has not authenticated with Duo.
    """
    try:
        del request.session['duo_authenticated']
    except KeyError:
        pass


# We could use just use django.contrib.auth.decorators.user_passes_test here
# if Duo authenticatedness was a property of the user, and there's probably
# a way to do that.
def duo_auth_required(view_func, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user has been authenticated with
    Duo, redirecting to the Duo authentication page if necessary.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if duo_authenticated(request):
                return view_func(request, *args, **kwargs)
            path = urlquote(request.get_full_path())
            return HttpResponseRedirect(
                '%s?%s=%s' % (
                    settings.DUO_LOGIN_URL, redirect_field_name, path))
        return wraps(
            view_func, assigned=available_attrs(view_func))(_wrapped_view)
    return decorator(view_func)


# There are a few more validations which could be done here as in
# django.contrib.auth.login, such as checking the form and redirect,
# and setting a test cookie.
@login_required
@require_http_methods(['GET', 'POST'])
def login(request):
    """
    View to authenticate the user locally and with Duo, redirecting to the next
    argument if given.
    For a GET, show the Duo form, which posts back with the Duo token.
    For a POST with successful authorization, redirect to the next argument,
    or show some default content.  Without successful authorization, redirect
    back here to try again.
    """
    if request.method == 'GET':
        next_url = request.GET.get('next')
        sig_request = duo_web.sign_request(
            settings.DUO_INTEGRATION_KEY, settings.DUO_SECRET, settings.SECRET_KEY,
            duo_username(request.user))
        template = loader.get_template('accounts/duo_login.html')
        context = RequestContext(
            request,
            {'next': next_url,
             'duo_js_src': static('js/vendor/Duo-Web-v1.bundled.js'),
             'duo_host': settings.DUO_API_HOST,
             'post_action': request.path,
             'sig_request': sig_request})
        return HttpResponse(template.render(context))
    elif request.method == 'POST':
        sig_response = request.POST.get('sig_response', '')
        duo_user = duo_web.verify_response(
            settings.DUO_INTEGRATION_KEY, settings.DUO_SECRET, settings.SECRET_KEY,
            sig_response)
        next_url = request.POST.get('next')
        if duo_user is None:
            # Redirect user to try again, keeping the next argument.
            # Note that we don't keep any other arguments.
            arg_map = {}
            if next_url:
                arg_map['next'] = next_url
            redirect_url = '%s?%s' % (
                request.path, urllib.urlencode(arg_map))
            return HttpResponseRedirect(redirect_url)
        else:
            duo_authenticate(request)
            if not next_url:
                next_url = settings.LOGIN_REDIRECT_URL
            return HttpResponseRedirect(next_url)
