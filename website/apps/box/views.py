import logging

from boxsdk.exception import BoxAPIException

from django.http import HttpResponse
from django.views.generic import View

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from accounts.models import User
from box.permissions import BoxEventCallbackPermission
from box.utils import auth_exercise, box_client_factory
from box.serializers import BoxEventModelSerializer
from core.utils import send_exception_notification
from storage.models import Storage


logger = logging.getLogger('sample.box.views')


class BoxAuthExercise(View):
    # pylint: disable=no-self-use
    def get(self, request):
        auth_exercise()
        return HttpResponse('empty by design')

box_auth_exercise = BoxAuthExercise.as_view()


class BoxEventCallback(APIView):
    """
    View for store events from BOX UI.
    """
    permission_classes = (BoxEventCallbackPermission, )
    serializer_class = BoxEventModelSerializer
    _log_prefix = 'BOX-EVENT-SAVE'

    def get_user(self, box_user_id):
        client = box_client_factory()
        try:
            box_user = client.user(user_id=box_user_id).get()
        except BoxAPIException as exc:
            logger.error('BOX-GET-USER-DETAILS-EXCEPTION exc %s', exc)
        return User.objects.filter(email=box_user.login).first()

    def get(self, request, *args, **kwargs):
        """
        Save all events from Box UI, triggered by user.
        """
        logger.debug('%s received GET from Box. Request: %s', self._log_prefix, request)
        serializer = self.serializer_class(data=request.query_params)
        if serializer.is_valid(raise_exception=False):
            # Temporary solution. Do not save user.
            # user = self.get_user(serializer.validated_data.get('box_user_id'))
            serializer.save()
            logger.debug('%s-SUCCESS received callback from Box', self._log_prefix)
        else:
            self._handle_errors(serializer.errors)
        # we should return success response on each request independent on results
        return Response(status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        Save all events from Box UI, triggered by user.
        """
        logger.debug('%s received POST from Box. Request: %s', request)
        serializer = self.serializer_class(data=request.query_params)
        if serializer.is_valid(raise_exception=False):
            # Temporary solution. Do not save user.
            # user = self.get_user(serializer.validated_data.get('box_user_id'))
            serializer.save()
            logger.debug('%s-SUCCESS received callback from Box', self._log_prefix)
        else:
            self._handle_errors(serializer.errors)
        # we should return success response on each request independent on results
        return Response(status=status.HTTP_200_OK)

    def _handle_errors(self, errors):
        errors_values = sum(errors.values(), [])

        if 'Storage matching query does not exist.' in errors_values:
            logger.debug('%s-FAILED %s', self._log_prefix, errors)
            # we can safely skip other checks and ignore this event
            return None
        elif any('required' in err for err in errors_values):
            logger.error('%s-FAILED not enough data has been provied: %s',
                         self._log_prefix,
                         errors)
            msg = 'Box webhooks params were configured wrong. Error {}. ' \
                  'Set up details: https://github.com/sample/sample/blob/master/' \
                  'documentation/BoxIntegration/documents-cp.md#endpoint-url'.format(errors)
            send_exception_notification(None, 'Box', msg)
        else:
            logger.error('%s-FAILED %s', self._log_prefix, errors)


box_event_callback_view = BoxEventCallback.as_view()
