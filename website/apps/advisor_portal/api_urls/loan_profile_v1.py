from django.conf.urls import url

from rest_framework_extensions.routers import ExtendedSimpleRouter

import advisor_portal.views.loan_profile_v1
from advisor_portal.views.loan_profile_v1 import (
    AdvisorLoanProfileV1View,

    AdvisorLoanProfileV1CreditRequestResponseView,

    AdvisorLoanProfileV1BorrowerV1View, BorrowerPreviousAddressesView,
    BorrowerPreviousEmploymentsView, BorrowerHoldingAssetsView,
    BorrowerVehicleAssetsView, BorrowerInsuranceAssetsView, BorrowerIncomesView,
    BorrowerExpensesView, BorrowerLiabilitiesView,

    AdvisorLoanProfileV1CoborrowerV1View, CoborrowerPreviousAddressesView,
    CoborrowerPreviousEmploymentsView, CoborrowerHoldingAssetsView,
    CoborrowerVehicleAssetsView, CoborrowerInsuranceAssetsView,
    CoborrowerIncomesView, CoborrowerExpensesView, CoborrowerLiabilitiesView,
)


urlpatterns = []


# complex


urlpatterns += [
    url(r'^advisor/loan-profiles-complex/$',
        advisor_portal.views.loan_profile_v1.advisor_loan_profile_complex_create_view,
        name='advisor_loan_profile_complex_create_view'),

    url(r'^advisor/loan-profiles-complex/(?P<pk>[0-9]+)/$',
        advisor_portal.views.loan_profile_v1.advisor_loan_profile_complex_view,
        name='advisor_loan_profile_complex_view'),
]

# RESTful

urlpatterns += [
    url(r'^advisor/loan-profiles-v1-sync-in-progress/$',
        advisor_portal.views.loan_profile_v1.advisor_loan_profile_v1_sync_in_progress_view,
        name='loanprofilev1-sync-in-progress-list'),
]

router = ExtendedSimpleRouter()

lp_route = router.register(
    # If this url will be changed, need also change
    # advisor_portal.permissions.ModifyOperationsPermission#has_permission
    r'advisor/loan-profiles-v1',
    AdvisorLoanProfileV1View,
    base_name='loanprofilev1'
)

credit_request_responses_route = lp_route.register(
    r'credit-request-responses',
    AdvisorLoanProfileV1CreditRequestResponseView,
    base_name='loan-profiles-v1-credit-request-responses',
    parents_query_lookups=['loan_profile']
)


borrowers_route = lp_route.register(
    r'borrowers',
    AdvisorLoanProfileV1BorrowerV1View,
    base_name='loan-profiles-v1-borrowers',
    parents_query_lookups=['loan_profile']
)

borrower_resources_parents_query_lookups = ['borrowerv1__loan_profile', 'borrowerv1']

borrowers_route.register(
    r'previous-addresses',
    BorrowerPreviousAddressesView,
    base_name='loan-profiles-v1-borrowers-previous-addresses',
    parents_query_lookups=borrower_resources_parents_query_lookups
)
borrowers_route.register(
    r'previous-employments',
    BorrowerPreviousEmploymentsView,
    base_name='loan-profiles-v1-borrowers-previous-employments',
    parents_query_lookups=borrower_resources_parents_query_lookups
)
borrowers_route.register(
    r'holding-assets',
    BorrowerHoldingAssetsView,
    base_name='loan-profiles-v1-borrowers-holding-assets',
    parents_query_lookups=borrower_resources_parents_query_lookups
)
borrowers_route.register(
    r'vehicle-assets',
    BorrowerVehicleAssetsView,
    base_name='loan-profiles-v1-borrowers-vehicle-assets',
    parents_query_lookups=borrower_resources_parents_query_lookups
)
borrowers_route.register(
    r'insurance-assets',
    BorrowerInsuranceAssetsView,
    base_name='loan-profiles-v1-borrowers-insurance-assets',
    parents_query_lookups=borrower_resources_parents_query_lookups
)
borrowers_route.register(
    r'incomes',
    BorrowerIncomesView,
    base_name='loan-profiles-v1-borrowers-incomes',
    parents_query_lookups=borrower_resources_parents_query_lookups
)
borrowers_route.register(
    r'expenses',
    BorrowerExpensesView,
    base_name='loan-profiles-v1-borrowers-expenses',
    parents_query_lookups=borrower_resources_parents_query_lookups
)
borrowers_route.register(
    r'liabilities',
    BorrowerLiabilitiesView,
    base_name='loan-profiles-v1-borrowers-liabilities',
    parents_query_lookups=borrower_resources_parents_query_lookups
)


coborrowers_route = borrowers_route.register(
    r'coborrowers',
    AdvisorLoanProfileV1CoborrowerV1View,
    base_name='loan-profiles-v1-coborrowers',
    parents_query_lookups=['borrower__loan_profile', 'borrower']
)

coborrowers_resources_parents_query_lookups = [
    'coborrowerv1__borrower__loan_profile', 'coborrowerv1__borrower', 'coborrowerv1'
]

coborrowers_route.register(
    r'previous-addresses',
    CoborrowerPreviousAddressesView,
    base_name='loan-profiles-v1-coborrowers-previous-addresses',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)
coborrowers_route.register(
    r'previous-employments',
    CoborrowerPreviousEmploymentsView,
    base_name='loan-profiles-v1-coborrowers-previous-employments',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)
coborrowers_route.register(
    r'holding-assets',
    CoborrowerHoldingAssetsView,
    base_name='loan-profiles-v1-coborrowers-holding-assets',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)
coborrowers_route.register(
    r'vehicle-assets',
    CoborrowerVehicleAssetsView,
    base_name='loan-profiles-v1-coborrowers-vehicle-assets',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)
coborrowers_route.register(
    r'insurance-assets',
    CoborrowerInsuranceAssetsView,
    base_name='loan-profiles-v1-coborrowers-insurance-assets',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)
coborrowers_route.register(
    r'incomes',
    CoborrowerIncomesView,
    base_name='loan-profiles-v1-coborrowers-incomes',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)
coborrowers_route.register(
    r'expenses',
    CoborrowerExpensesView,
    base_name='loan-profiles-v1-coborrowers-expenses',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)
coborrowers_route.register(
    r'liabilities',
    CoborrowerLiabilitiesView,
    base_name='loan-profiles-v1-coborrowers-liabilities',
    parents_query_lookups=coborrowers_resources_parents_query_lookups
)


urlpatterns += router.urls
