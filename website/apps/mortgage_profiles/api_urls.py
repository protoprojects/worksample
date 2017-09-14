from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns
from mortgage_profiles.views import (
    MortgageProfilePurchaseView,
    MortgageProfilePurchaseDetailsView,
    MortgageProfileRefinanceView,
    MortgageProfileRefinanceDetailsView,
    MortgageProfileActiveRetrieveView,
)
from mortgage_profiles.views import (
    RateQuoteRequestView,
    StateLicensesView,
    RateQuoteServiceView,
    RateQuoteLessResultView,
    RateQuoteFullResultView,
    RateQuoteResultsView
)


urlpatterns = format_suffix_patterns([
    url(r'^purchase/$', MortgageProfilePurchaseView.as_view(), name='purchase_list'),
    url(r'^purchase/(?P<uuid>[a-km-zA-HJ-NP-Z2-9]{22})/$',
        MortgageProfilePurchaseDetailsView.as_view(), name='purchase_details'),
    url(r'^refinance/$', MortgageProfileRefinanceView.as_view(), name='refinance_list'),
    url(r'^refinance/(?P<uuid>[a-km-zA-HJ-NP-Z2-9]{22})/$',
        MortgageProfileRefinanceDetailsView.as_view(), name='refinance_details'),
    url(r'^active/$', MortgageProfileActiveRetrieveView.as_view(), name='active_retrive'),
    url(r'^rate-quote-service/$', RateQuoteServiceView.as_view(), name='rate_quote_service'),
    url(r'^rate-quote-service-less/$', RateQuoteLessResultView.as_view(), name='rate_quote_service_less'),
    url(r'^rate-quote-service-full/$', RateQuoteFullResultView.as_view(), name='rate_quote_service_full'),
    url(r'^states/$', StateLicensesView.as_view(), name='licensed_states'),
    url(r'^rate-quote/(?P<uuid>[a-km-zA-HJ-NP-Z2-9]{22})/$', RateQuoteResultsView.as_view(), name='rate_quote'),
    url(r'^rate-quote-request/$', RateQuoteRequestView.as_view(), name='rate_quote_request'),
])
