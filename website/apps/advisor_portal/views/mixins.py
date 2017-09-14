from django.conf import settings
from accounts.authentication_mixins import WebTokenAuthenticationMixin


class AdvisorSetMixin(object):
    def perform_create(self, serializer):
        return serializer.save(advisor_id=self.request.user.id)

    def perform_update(self, serializer):
        return serializer.save(advisor_id=self.request.user.id)


class AdvisorTokenAuthMixin(WebTokenAuthenticationMixin):
    throttle_scope = settings.REST_FRAMEWORK_ADVISOR_PORTAL_THROTTLE
