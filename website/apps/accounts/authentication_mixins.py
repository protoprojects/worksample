from accounts.authentication import CustomWebTokenAuthentication


class WebTokenAuthenticationMixin(object):
    authentication_classes = (CustomWebTokenAuthentication,)
