"""
The endpoints for the Google Analytics Proxy.
Supports ga-proxy/events, ga-proxy/pageviews, and ga-proxy/tags
"""

import logging

from django.conf import settings

from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser

from accounts.authentication import CustomWebTokenAuthentication

from ga_proxy.gamp import GampEvent, GampPageview, GampTag, GampMessage, GampRawTag
from ga_proxy.gamp_transport import send, PROXY_MODE_OFF

logger = logging.getLogger('ga-proxy-logger')


class GoogleAnalyticsPostMixin(object):
    """
    A Mixin for logic supporting the proxying of Google Analytics hits.
    """

    authentication_classes = (CustomWebTokenAuthentication,)
    permission_classes = (AllowAny,)
    serializer_class = None
    proxy_mode = getattr(settings, 'GA_PROXY_MODE', PROXY_MODE_OFF)
    logger.info("GA-PROXY-STARTUP-MODE mode " + proxy_mode)

    # pylint: disable=no-self-use
    def create_ga_tag(self, gamp_msg):
        """
        gamp_msg: A GampMessage Object
        Take a message object, and if it reports valid contents for its type,
        send an event hit to Google.
        """
        if gamp_msg.is_valid:
            send(gamp_msg.payload)
            return Response({"status": "created"}, status=status.HTTP_201_CREATED)

        else:
            logger.error(
                'GA-PROXY-MALFORMED-TAG error \"' + gamp_msg.get_error_message() + '\"')
            return Response({"details": gamp_msg.get_error_message()},
                            status=status.HTTP_400_BAD_REQUEST)

    def create_ga_proxy_tag(self, msg, request):
        """
        msg: A GampMessage Object
        request: the POST Request message
        Set additional values based on the requester (request IP and Agent)
        in the Gamp Message, then pass it along for transmission
        """
        msg.set_proxy_values(
            ip=request.META['REMOTE_ADDR'], ua=request.META['HTTP_USER_AGENT'])
        return self.create_ga_tag(msg)


class GoogleAnalyticsRawTagView(GoogleAnalyticsPostMixin, CreateAPIView):
    """
    Proxy all posted tag key-value pairs
    """

    def post(self, request, *args, **kwargs):
        """
        Create a generic tag.  Key values are not processed
        """
        if self.proxy_mode == self.PROXY_MODE_OFF:
            return Response({"status": "ignored"}, status=status.HTTP_202_ACCEPTED)

        try:
            data = JSONParser().parse(request)
            msg = GampRawTag(data)
            return self.create_ga_proxy_tag(msg, request)
        except TypeError as excepted:
            logger.error(
                'GA-PROXY-MALFORMED-POST error "%s" input', unicode(excepted))
            return Response({'details': unicode(excepted)}, status=status.HTTP_400_BAD_REQUEST)


class BaseGoogleAnalyticsConfiguredTagView(GoogleAnalyticsPostMixin, CreateAPIView):
    """
    Configured tag views override key values sent in the request with
    configured values like the GA Tracking ID.
    """

    model = GampMessage

    def post(self, request, *args, **kwargs):
        """
        Create a configured hit.  Key values are processed
        """
        if self.proxy_mode == PROXY_MODE_OFF:
            return Response({"status": "ignored"}, status=status.HTTP_202_ACCEPTED)

        try:
            data = JSONParser().parse(request)
            msg = self.model(data, settings.GA_PROXY_TRACKING_ID)
            return self.create_ga_proxy_tag(msg, request)
        except TypeError as excepted:
            logger.error(
                'GA-PROXY-MALFORMED-POST error "%s"', unicode(excepted))
            return Response({'details': unicode(excepted)}, status=status.HTTP_400_BAD_REQUEST)


class GoogleAnalyticsEventView(BaseGoogleAnalyticsConfiguredTagView):
    """
    Endpoint for creating a Google Analytics Event hit.
    """

    model = GampEvent


class GoogleAnalyticsPageviewView(BaseGoogleAnalyticsConfiguredTagView):
    """
    Endpoint for creating a Google Analytics Pageview hit.
    """

    model = GampPageview


class GoogleAnalyticsTagView(BaseGoogleAnalyticsConfiguredTagView):
    """
    Endpoint for free form GA tag hit
    """

    model = GampTag
