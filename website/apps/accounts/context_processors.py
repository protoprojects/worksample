from core.renderers import CamelCaseJSONRenderer


def active_profile(request):
    if request.user.is_authenticated():
        result = {
            'is_logged_in': True,
            'name': request.user.get_full_name(),
            'email': request.user.email,
            'account_number': request.user.account_number if request.user.is_customer() else None,
        }
        if request.user.is_customer() and request.user.phone:
            result['phone'] = request.user.phone
    else:
        result = {
            'is_logged_in': False,
            'account_number': request.session.get("account_number"),
        }
    return {
        'activeProfile': CamelCaseJSONRenderer().render(result)
    }
