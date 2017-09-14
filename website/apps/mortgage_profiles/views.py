import logging
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.http import Http404

from rest_framework import generics, permissions, status, response, views
from rest_framework.exceptions import ValidationError

from core.parsers import CamelCaseFormParser
from mortgage_profiles.models import (
    MortgageProfilePurchase,
    MortgageProfileRefinance,
    MortgageProfile,
    RateQuoteRequest,
)
from mortgage_profiles.serializers import (
    MortgageProfileSerializer,
    MortgageProfilePurchaseSerializer,
    MortgageProfileRefinanceSerializer,
    RateQuoteLenderSerializer
)
from mortgage_profiles.permissions import IsMortgageProfileOwner, HasNoLoanProfile
from mortgage_profiles.mortech import MortechApi, MortechDirector, MortechScenario
from pages.models.licenses import StateLicense
from pages.serializers import StateLicenseSerializer

logger = logging.getLogger("sample.mortgage_profiles.views")


class MortgageProfileMixin(object):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():

            if request.user.is_authenticated() and request.user.is_customer():
                serializer.save(user=request.user)
            else:
                # pylint: disable=attribute-defined-outside-init
                self.object = serializer.save()

            # Put mortgage profile uuid to session. Only owner can see mortgage profile.
            request.session['mortgage_profile_uuid'] = self.object.uuid

            headers = self.get_success_headers(serializer.data)
            logger.info('MORTGAGE-PROFILE-INITIAL-POST-CREATED request_data %s', request.data)
            return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        logger.error('MORTGAGE-PROFILE-INITIAL-POST-FAILED-TO-CREATE request_data %s response_data %s',
                     request.data,
                     serializer.errors)

        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


###################################
# Mortgage Profile - Create Views #
###################################
class MortgageProfilePurchaseView(MortgageProfileMixin, generics.CreateAPIView):
    model = MortgageProfilePurchase
    serializer_class = MortgageProfilePurchaseSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.all()


class MortgageProfileRefinanceView(MortgageProfileMixin, generics.CreateAPIView):
    model = MortgageProfileRefinance
    serializer_class = MortgageProfileRefinanceSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.all()


###################################
# Mortgage Profile - Detail Views #
###################################
class MortgageProfilePurchaseDetailsView(generics.RetrieveUpdateAPIView):
    model = MortgageProfilePurchase
    serializer_class = MortgageProfilePurchaseSerializer
    permission_classes = (IsMortgageProfileOwner, HasNoLoanProfile,)
    queryset = MortgageProfilePurchase.objects.all()
    lookup_field = 'uuid'


class MortgageProfileRefinanceDetailsView(generics.RetrieveUpdateAPIView):
    model = MortgageProfileRefinance
    serializer_class = MortgageProfileRefinanceSerializer
    permission_classes = (IsMortgageProfileOwner, HasNoLoanProfile,)
    queryset = MortgageProfileRefinance.objects.all()
    lookup_field = 'uuid'


###################################
# Mortgage Profile - Active View  #
###################################
class MortgageProfileActiveRetrieveView(views.APIView):
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'uuid'

    # pylint: disable=no-self-use
    def get(self, request):
        """
        Return active mortgage profile if exists.

        """
        # Always return empty mortgage profile for now.
        if request.session.get('mortgage_profile_uuid'):
            mortgage_profile = get_object_or_404(
                MortgageProfile,
                uuid=request.session['mortgage_profile_uuid']
            )

            return response.Response({
                'exists': True,
                'kind': mortgage_profile.kind,
                'id': mortgage_profile.uuid
            }, status=status.HTTP_200_OK)
        else:
            return response.Response({
                'exists': False,
            }, status=status.HTTP_200_OK)


###################################
# RateQuoteService Views          #
###################################
class RateQuoteServiceMixin(object):
    @staticmethod
    def get_rate_quote_results(mortgage_profile):
        '''
        1 Sends form data to RateQuote
        2 Validates response
        3 Saves lenders
        4 Generates rate quote results
        '''
        rate_quote_api = MortechApi(mortgage_profile=mortgage_profile)

        if not rate_quote_api.is_valid():
            errors = rate_quote_api.get_errors()
            return response.Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Convert XML response to dict
        rate_quote_response = rate_quote_api.get_response()

        if not rate_quote_response.is_valid():
            errors = rate_quote_response.get_errors()
            return response.Response(errors, status=status.HTTP_400_BAD_REQUEST)

        rate_quote_result = MortechDirector(mortgage_profile)

        if not rate_quote_result.is_valid():
            errors = rate_quote_result.get_errors()
            logger.info('RATE-QUOTE-RESULT-ERRORS %s', errors)
            return response.Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # 3 Get rate quotes
        result = rate_quote_result.get_scenario()
        return response.Response(result, status=status.HTTP_200_OK)


class RateQuoteServiceView(RateQuoteServiceMixin, views.APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        uuid = request.session.get('mortgage_profile_uuid')
        mortgage_profile = get_object_or_404(MortgageProfile.objects.select_subclasses(), uuid=uuid)
        return self.get_rate_quote_results(mortgage_profile=mortgage_profile)


class RateQuoteResultMixin(object):
    def get_rate_quote_results(self, mortgage_profile, term, amortization_type):
        # pylint: disable=attribute-defined-outside-init
        self.rate_quote_result = MortechDirector(mortgage_profile)
        if self.rate_quote_result.is_valid():
            results = self.get_specific_results(term, amortization_type)
            return response.Response(results, status=status.HTTP_200_OK)
        else:
            errors = self.rate_quote_result.get_errors()
            return response.Response(errors, status=status.HTTP_400_BAD_REQUEST)


class MortgageProfileRateQuoteResultMixin(RateQuoteResultMixin):
    def get(self, request, *args, **kwargs):
        try:
            mortgage_profile = MortgageProfile.objects.get_subclass(uuid=request.session['mortgage_profile_uuid'])
        except MortgageProfile.DoesNotExist:
            raise Http404()
        else:
            term = self.request.GET.get('term')
            amortization_type = self.request.GET.get('amortizationType')
            return self.get_rate_quote_results(mortgage_profile, term, amortization_type)


class RateQuoteLessResultView(MortgageProfileRateQuoteResultMixin, views.APIView):
    permission_classes = (IsMortgageProfileOwner,)

    def get_specific_results(self, term, amortization_type):
        return self.rate_quote_result.get_scenario(term, amortization_type)


class RateQuoteFullResultView(MortgageProfileRateQuoteResultMixin, views.APIView):
    permission_classes = (IsMortgageProfileOwner,)

    def get_specific_results(self, term, amortization_type):
        return self.rate_quote_result.get_full_scenario(term, amortization_type)


class StateLicensesView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = StateLicenseSerializer
    queryset = StateLicense.objects.exclude(end_date__lt=datetime.now())


class RateQuoteMixin(object):
    """Returns rate quote request and rate quote view results."""

    def get_results(self, term=None, amortization=None):
        """
        Returns rate quote results. Every result object includes the par_lender and matching scenarios.

        :param term: str, term
        :param amortization: str, amortization
        :return: rate quotes
        :rtype: `dict`
        """
        lender = self.rate_quote_request.get_par_lender(term, amortization)
        scenarios = self.rate_quote_request.get_scenarios(term, amortization)
        par_lender = self.serializer(lender).data
        data = self.serializer(scenarios, many=True).data

        results = {
            'par_lender': par_lender if par_lender else None,
            'request_uuid': self.rate_quote_request.uuid,
            'results': data if data else None,
            'term': par_lender['term'] if par_lender else None,
            'amortization_type': par_lender['amortization_type'] if par_lender else None
        }

        return response.Response(results, status=status.HTTP_200_OK)

    def get_unique_results(self):
        """
        Return best rate quote scenarios for each term and amortization.

        - Standard Scenarios:
            * 30 Year, Fixed
            * 15 Year, Fixed
            * 7 Year, Variable
            * 5 Year, Variable
            * amortization: Fixed, Variable

        :return: `dict` rate quotes
        :rtype: DRF Response
        """
        options = {
            '30 Year': 'Fixed',
            '15 Year': 'Fixed',
            '7 Year': 'Variable',
            '5 Year': 'Variable'
        }
        lenders = []
        for term, amortization in options.iteritems():
            lender = self.rate_quote_request.get_par_lender(term, amortization)
            lenders.append(lender if lender else None)

        lenders = self.serializer(lenders, many=True).data
        results = {
            'request_uuid': self.rate_quote_request.uuid,
            'results': lenders if lenders else None
        }
        return response.Response(results, status=status.HTTP_200_OK)


class RateQuoteRequestView(RateQuoteServiceMixin, RateQuoteMixin, generics.ListCreateAPIView):
    """
    View for handling requests for rate quotes. Creates `MortgageProfile`
    from inbound request data.
    """

    model = RateQuoteRequest
    serializer = RateQuoteLenderSerializer
    permission_classes = (permissions.AllowAny,)
    parser_classes = (CamelCaseFormParser,)

    def post(self, request, *args, **kwargs):
        """
        Takes a POST request from external partner websites to return rate
        quote results to the consumer portal.

        - Minimum fields required::

            * Purchase: kind, property_state, property_value, purchase_downpayment,
                  credit_score, property_occupation
            * Refi: kind, property_state, property_value, property_occupation,
              credit_score, purpose, mortgage_owe

        :param request: HTTP request containing `MortgageProfile` attributes
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        :return: JSON object with rate quotes
        :raises: HTTP 400 Bad Request on insufficient or missing data

        .. todo:: Part of refactoring to a RateQuoteService 281956101674944
        """
        serializer = self.get_serializer_class(request.data)
        if serializer.is_valid():
            mp = serializer.save()
            # TODO: Part of refactor 281956101674944
            res = self.get_rate_quote_results(mp)
            if res.status_code == 400:
                return response.Response(res.data, status=status.HTTP_400_BAD_REQUEST)
            uuid = res.data.get('request_uuid')
            self.rate_quote_request = get_object_or_404(self.model, uuid=uuid)
            return self.get_unique_results()
        else:
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self, request_data):
        """
        Returns proper serializer.

        :param request_data: `dict`, mortgage profile data
        :return: DRF serializer
        :raises HTTP_400: HTTP 400 for `KeyError`
        """
        try:
            kind = request_data['kind']
        except KeyError as exc:
            logger.info("RATE-QUOTE-SERVICE-INVALID-DATA: %s is not purchase or refinance", exc)
            raise ValidationError(detail="MortgageProfile 'kind' is missing or invalid. Valid values: 'purchase', 'refinance'")
        else:
            if kind == MortgageProfile.PURCHASE:
                purchase_data = request_data.copy()
                purchase_data.update({
                    'target_value': purchase_data.get('property_value')
                })
                return MortgageProfilePurchaseSerializer(data=purchase_data)
            elif kind == MortgageProfile.REFINANCE:
                return MortgageProfileRefinanceSerializer(data=request_data)


class RateQuoteResultsView(RateQuoteMixin, generics.ListAPIView):
    """Returns rate quotes."""

    model = RateQuoteRequest
    permission_classes = (permissions.AllowAny,)
    serializer = RateQuoteLenderSerializer
    queryset = model.objects.all()

    def get(self, request, *args, **kwargs):
        """
        Returns rate quote results by it's UUID.

        :param request: `dict`, term and amortization
        :param args: `string`, term or amortization
        :param kwargs: `dict`, rate quote request uuid
        :return: `dict`, rate quotes
        :rtype: DRF Response object
        """
        self.rate_quote_request = get_object_or_404(self.model, uuid=self.kwargs['uuid'])
        term, amortization = request.GET.get('term'), request.GET.get('amortizationType')

        return self.get_results(term, amortization)
