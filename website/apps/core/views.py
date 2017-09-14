from django.conf import settings
from django.http import HttpResponse
from django.views.generic import View
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from rest_framework import authentication
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.settings import api_settings
from rest_framework_jwt.views import ObtainJSONWebToken

from core.serializers import VerifyJSONWebTokenSerializer


class EmailTestingView(View):
    template = ""

    def get(self, request, *args, **kwargs):
        email = self.kwargs.get("email")

        if not email:
            raise NotImplementedError("Forgot email? Don't!")

        msg = EmailMultiAlternatives(
            subject="Just testing",
            body="Nothing interesting here",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        msg.attach_alternative(render_to_string(self.template), "text/html")

        msg.send()

        return HttpResponse("Sent!")


class JSONWebTokenLoginView(ObtainJSONWebToken):
    """
    Basic API View that receives a POST with a user's username and password.

    Returns a JSON Web Token that can be used for authenticated requests.
    """

    serializer_class = None  # just a reminder that inheritors must define own serializer
    authentication_classes = (authentication.BasicAuthentication, )
    throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES


class VerifyJSONWebTokenView(GenericAPIView):
    permission_classes = ()
    serializer_class = VerifyJSONWebTokenSerializer
    authentication_classes = ()

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return Response(status=204)
        return Response(serializer.errors, status=400)
