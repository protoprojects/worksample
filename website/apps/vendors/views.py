import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from vendors.serializers import SalesforceOpportunitySerializer

logger = logging.getLogger("sample.vendors.views")


class VendorSalesforceView(APIView):
    """
    Create and retrieve questionnaire from Salesforce lead.

    Accepts guid POST request from Salesforce lead and returns:
    * sample-guid: a UUID for the created LoanProfileV1
    * sample-url: a URL to the questionnaire based on the created LoanProfileV1
    * sample-registration-direct-url: a URL for direct registration on sample one portal

    If the serializer raises an exception, rest_framework will handle and return
    to the client:
    * HTTP_400_BAD_REQUEST
    * errors for fields that failed validation

    """
    permission_classes = ()

    @staticmethod
    def post(request, *args, **kwargs):
        # logger.debug('SALESFORCE-POST-INCOMING-REQUEST-DATA %s', pprint.pformat(request.data))
        serializer = SalesforceOpportunitySerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.save()  # serializer.save() calls serializer.create()
            response_data = {
                'status': 'success',
                'sample-guid': validated_data['sample-guid'],
                'sample-url': validated_data['sample-url'],
                'sample-registration-direct-url': validated_data['sample-registration-direct-url']
            }
            # logger.debug('SALESFORCE-POST-SUCCESS %s', pprint.pformat(response_data))
            return Response(data=response_data, status=status.HTTP_201_CREATED)
        else:
            # logger.debug('SALESFORCE-POST-ERRORS %s', pprint.pformat(serializer.errors))
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

vendor_salesforce_create_view = VendorSalesforceView.as_view()
