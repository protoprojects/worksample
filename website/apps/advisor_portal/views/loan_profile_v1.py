import logging
import datetime

from django.db.models import Prefetch, BooleanField, Case, Value, When, Q
from django.http import Http404

from rest_framework import viewsets, decorators, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings

from rest_framework_extensions.mixins import NestedViewSetMixin

from advisor_portal.views.mixins import AdvisorTokenAuthMixin
from advisor_portal.filters import LoanProfileInProgressFilter
from advisor_portal.views import CRUD_ACTIONS, ENDPOINT_PROPERTY_METHODS
from advisor_portal.views.mixins import AdvisorSetMixin
from advisor_portal.views.loan_profile_v1_common import (
    AdvisorLoanProfileV1BorrowerBaseView, BorrowerResourcesMixin,
    CoborrowerResourcesMixin, CommonAddressView,
    RestrictKindCreation, RestrictIncomesKindCreation,
    HoldingAssetsOwnershipMixin, SelectForUpdateMixin, LiabilitiesRestrictionMixin,
)
from advisor_portal.paginators import (
    SmallLimitOffsetPagination, LargePagePagination
)
from advisor_portal.permissions import (
    AllowAdvisorPermission, LoanProfileModifyOperationsPermission,
)
from advisor_portal.serializers.loan_profile_v1 import (
    AddressV1Serializer,
    AdvisorLoanProfileV1ComplexSerializer,
    BorrowerV1Serializer,
    CoborrowerV1Serializer,
    CreditRequestResponseSerializer,
    EmploymentV1Serializer,
    ExpenseV1Serializer,
    HoldingAssetV1Serializer,
    InsuranceAssetV1Serializer,
    VehicleAssetV1Serializer,
    IncomeV1Serializer,
    LiabilityV1Serializer,
    LoanProfileV1Serializer,
)
from loans.models import (
    AddressV1, BorrowerV1, CoborrowerV1, EmploymentV1, ExpenseV1,
    HoldingAssetV1, InsuranceAssetV1, VehicleAssetV1,
    IncomeV1, LiabilityV1, LoanProfileV1,
)
from mismo_credit.models import CreditRequestResponse
from mismo_credit.tasks import start_credit_pull
from box.api_v1 import box_file_get

logger = logging.getLogger('sample.advisor_portal.views')

#
# Complex
#


class AdvisorLoanProfileV1ComplexView(AdvisorTokenAuthMixin,
                                      AdvisorSetMixin,
                                      viewsets.GenericViewSet,
                                      viewsets.mixins.RetrieveModelMixin,
                                      viewsets.mixins.CreateModelMixin,):
    """
    This is a complex view, which accepts JSON which
    describes loan profile and creating loan profile
    with all related objects automatically.
    """

    permission_classes = (IsAuthenticated, AllowAdvisorPermission,)
    serializer_class = AdvisorLoanProfileV1ComplexSerializer

    def create(self, request, *args, **kwargs):
        """
        Overriding to do avoid incomplete data response,
        returning ID will be enough.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'id': serializer.data['id']}, status=status.HTTP_201_CREATED, headers=headers)

    def retrieve(self, request, *args, **kwargs):
        """
        Overriding to do a hack with related borrower and coborrower
        objects.
        """
        instance = self.get_object()
        instance.borrower = instance.borrowers.last()
        if instance.borrower:
            instance.coborrower = instance.borrower.coborrower
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_queryset(self):
        return self.request.user.loan_profilesV1.all()

advisor_loan_profile_complex_create_view = AdvisorLoanProfileV1ComplexView.as_view({'post': 'create'})
advisor_loan_profile_complex_view = AdvisorLoanProfileV1ComplexView.as_view({'get': 'retrieve'})

#
# RESTful
#


# Main

class AdvisorLoanProfileV1View(AdvisorTokenAuthMixin,
                               SelectForUpdateMixin,
                               AdvisorSetMixin,
                               NestedViewSetMixin,
                               viewsets.GenericViewSet,
                               viewsets.mixins.CreateModelMixin,
                               viewsets.mixins.UpdateModelMixin,
                               viewsets.mixins.ListModelMixin,
                               viewsets.mixins.RetrieveModelMixin,
                               viewsets.mixins.DestroyModelMixin):
    """
    Base loan profile view.
    """

    permission_classes = [IsAuthenticated, AllowAdvisorPermission, LoanProfileModifyOperationsPermission, ]
    serializer_class = LoanProfileV1Serializer
    filter_class = LoanProfileInProgressFilter
    pagination_class = SmallLimitOffsetPagination
    filter_backends = [filters.OrderingFilter] + api_settings.DEFAULT_FILTER_BACKENDS
    ordering = ('-respa_triggered_within_last_week', '-updated')
    ordering_fields = ('updated', 'borrowers__first_name', 'borrowers__last_name',)

    qs_filter_kwargs = {
        'is_active': True,
        'encompass_sync_status__in': [
            LoanProfileV1.ENCOMPASS_SYNCED,
            LoanProfileV1.ENCOMPASS_NEVER_SYNCED,
            LoanProfileV1.ENCOMPASS_SYNC_FAILED,
        ]
    }
    prefetch_list = [
        Prefetch('new_property_address'),

        Prefetch('borrowers'),
        Prefetch('borrowers__mailing_address'),
        Prefetch('borrowers__demographics'),
        Prefetch('borrowers__realtor'),
        Prefetch('borrowers__realtor__address'),
        Prefetch('borrowers__previous_addresses'),
        Prefetch('borrowers__previous_employment'),
        Prefetch('borrowers__holding_assets'),
        Prefetch('borrowers__vehicle_assets'),
        Prefetch('borrowers__insurance_assets'),
        Prefetch('borrowers__income'),
        Prefetch('borrowers__expense'),
        Prefetch(
            'borrowers__coborrower',
            queryset=CoborrowerV1.objects.filter(is_active=True)
        ),
        Prefetch('borrowers__coborrower__mailing_address'),
        Prefetch('borrowers__coborrower__demographics'),
        Prefetch('borrowers__coborrower__realtor'),
        Prefetch('borrowers__coborrower__realtor__address'),
        Prefetch('borrowers__coborrower__previous_addresses'),
        Prefetch('borrowers__coborrower__previous_employment'),
        Prefetch('borrowers__coborrower__holding_assets'),
        Prefetch('borrowers__coborrower__vehicle_assets'),
        Prefetch('borrowers__coborrower__insurance_assets'),
        Prefetch('borrowers__coborrower__income'),
        Prefetch('borrowers__coborrower__expense'),

        Prefetch('credit_request_responses'),
    ]

    def _get_paginated_lp_ids(self):
        """
        To reduce time on ordering and slicing,
        it is faster to take needed IDs first
        to avoid decryption, and then simply select
        needed loan profiles.
        Filtered and sorted ids are paginated in the
        way we're paginating simple queryset.
        """
        qs = self.request.user.loan_profilesV1.filter(
            **self.qs_filter_kwargs
        ).values_list(
            'id', flat=True
        )
        qs = self.annotate_queryset(qs)
        qs = self.filter_queryset(qs)
        return self.paginate_queryset(qs)

    def annotate_queryset(self, qs):
        today = datetime.date.today()
        week_ago = today - datetime.timedelta(days=7)

        is_respa_triggered_within_last_week_expr = Case(
            When(Q(_respa_triggered=True) & Q(updated__gt=week_ago), then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )

        return qs.annotate(respa_triggered_within_last_week=is_respa_triggered_within_last_week_expr)

    def get_paginated_qs(self):
        assert hasattr(self, '_get_paginated_lp_ids'), "%s has not '_get_paginated_lp_ids' attribute" % self
        qs = self.request.user.loan_profilesV1.prefetch_related(
            *self.prefetch_list
        ).filter(
            id__in=self._get_paginated_lp_ids()
        )
        qs = self.annotate_queryset(qs)
        qs = filters.OrderingFilter().filter_queryset(self.request, qs, self)
        return qs

    def get_queryset(self):
        return self.request.user.loan_profilesV1.prefetch_related(
            *self.prefetch_list
        ).filter(
            **self.qs_filter_kwargs
        )

    def list(self, request, *args, **kwargs):
        """
        Overriding method because we don't need to paginate
        queryset since we selecting needed loan profiles by
        using `self._get_paginated_lp_ids()`.
        """
        assert hasattr(self, 'get_paginated_qs'), "%s has not 'get_paginated_qs' attribute" % self
        queryset = self.get_paginated_qs()
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response(serializer.data)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

    # properties

    @decorators.detail_route(methods=['post'], permission_classes=[IsAuthenticated, AllowAdvisorPermission])
    def storage(self, *args, **kwargs):
        instance = self.get_object()
        instance.create_storage()
        if not instance.storage:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        data = {'id': instance.storage.box_folder_id}
        return Response(data=data, status=status.HTTP_201_CREATED)

    # pylint: disable=no-self-use
    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def new_property_address(self, request, *args, **kwargs):
        """
        Endpoint-property, new property address of loan profile entry.
        """

        view = CommonAddressView
        view.filters = {'loanprofilev1': kwargs['pk']}
        view.related_set_attr = 'loanprofilev1_set'
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)

    # actions

    @decorators.detail_route(methods=['post'])
    def los_guid(self, *args, **kwargs):
        """
        POST for LOS GUID
        """
        data = {}
        instance = self.get_object()
        if instance.encompass_sync_status not in [
                LoanProfileV1.ENCOMPASS_NEVER_SYNCED,
                LoanProfileV1.ENCOMPASS_SYNC_FAILED
        ]:
            logger.warning('LOS-GUID-REQUEST-SYNC-BAD-STATUS %s', instance.guid)
            data['request_submitted'] = False
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        preflight_warnings = instance.encompass_sync_warnings()
        if preflight_warnings:
            data['request_submitted'] = False
            data['warnings'] = preflight_warnings
            logger.warning('LOS-GUID-PREFLIGHT-WARNINGS %s %s',
                           instance.guid, preflight_warnings)
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        try:
            submitted = instance.sync_to_encompass()
        except Exception:
            submitted = False
        data['request_submitted'] = submitted
        http_status = status.HTTP_201_CREATED if submitted else status.HTTP_400_BAD_REQUEST
        return Response(data=data, status=http_status)

    @decorators.detail_route(methods=['post'])
    def confirm_demographics_questions(self, *args, **kwargs):
        instance = self.get_object()
        instance.is_demographics_questions_request_confirmed = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.detail_route(methods=['post'])
    def credit_request(self, *args, **kwargs):
        instance = self.get_object()
        return start_credit_pull(instance.guid)

    @decorators.detail_route(methods=['patch'])
    def trigger_respa(self, *args, **kwargs):
        instance = self.get_object()
        data = instance.respa_criteria_for_advisor_portal()
        http_status = status.HTTP_200_OK if instance.trigger_respa_for_advisor_portal() else status.HTTP_400_BAD_REQUEST
        return Response(data=data, status=http_status)

    @decorators.detail_route(methods=['get'])
    def advisor_credit_pdf_view_url(self, *args, **kwargs):
        instance = self.get_object()
        summary = instance.find_valid_credit_report_summary()

        if summary is None:
            logging.exception("MISMO-CREDIT-SHARED-LINK-FAIL-NO-SUMMARY lp %s", instance.id)
            data = {'url': ""}
            resp_status = status.HTTP_404_NOT_FOUND
        else:
            #TODO: https://app.asana.com/0/26776562531082/310821218441711
            box_file = box_file_get(summary.report_pdf_document.document_id)
            shared_link = box_file.get_shared_link(access='company', allow_preview=True)
            data = {'url': shared_link}
            resp_status = status.HTTP_200_OK

        return Response(data=data, status=resp_status)

    @decorators.detail_route(methods=['post'])
    def unlock_loan(self, *args, **kwargs):
        instance = self.get_object()
        if instance.lock_owner != instance.LOCK_OWNER_CHOICES.advisor:
            instance.update_from_mortgage_profile()
            instance.lock_owner = instance.LOCK_OWNER_CHOICES.advisor
            instance.save()
        data = {'lock_owner': instance.lock_owner}
        return Response(data, status=status.HTTP_200_OK)


class AdvisorLoanProfileV1SyncInProgressView(AdvisorLoanProfileV1View):
    """
    Loan profile view which represents LoanProfile's,
    which are currently syncing with encompass.
    """
    permission_classes = [IsAuthenticated, AllowAdvisorPermission, ]
    serializer_class = LoanProfileV1Serializer
    pagination_class = LargePagePagination
    ordering = ('-updated')

    qs_filter_kwargs = {
        'is_active': True,
        'encompass_sync_status__in': [
            LoanProfileV1.ENCOMPASS_READY_TO_SYNC,
            LoanProfileV1.ENCOMPASS_SYNC_IN_PROGRESS,
            LoanProfileV1.ENCOMPASS_SYNC_FAILED,
        ]
    }


advisor_loan_profile_v1_sync_in_progress_view = AdvisorLoanProfileV1SyncInProgressView.as_view({'get': 'list'})


# Credit Request

class AdvisorLoanProfileV1CreditRequestResponseView(
        AdvisorTokenAuthMixin,
        NestedViewSetMixin,
        viewsets.ReadOnlyModelViewSet):
    """
    Credit Report View
    """

    permission_classes = [IsAuthenticated, AllowAdvisorPermission]
    serializer_class = CreditRequestResponseSerializer
    model = CreditRequestResponse

    def get_queryset(self):
        return self.filter_queryset_by_parents_lookups(
            self.model.objects.all().prefetch_related(
                Prefetch('credit_report_summary'),
                Prefetch('credit_report_summary__credit_report_scores'),
            )
        )

# Borrower


class AdvisorLoanProfileV1BorrowerV1View(AdvisorLoanProfileV1BorrowerBaseView):
    """
    Base borrower view.
    """

    serializer_class = BorrowerV1Serializer
    model = BorrowerV1
    properties_mapping = {
        'address': 'borrowerv1_address',
        'mailing_address': 'borrowerv1_mailing_address',
        'demographics': 'borrowerv1',
        'employment': 'borrowerv1_employment',
        'realtor': 'borrowerv1_realtor',
    }

    def perform_create(self, serializer):
        loan_profile_id = self.kwargs['loan_profile']
        try:
            loan_profile = LoanProfileV1.objects.get(id=loan_profile_id)
        except LoanProfileV1.DoesNotExist:
            raise Http404('Loan profile with id "{}" does not exist'.format(loan_profile_id))
        else:
            serializer.save(loan_profile=loan_profile)


class BorrowerPreviousAddressesView(BorrowerResourcesMixin):
    """
    Base view of borrower previous addresses.
    """

    serializer_class = AddressV1Serializer
    model = AddressV1
    m2m_rel_attr = 'previous_addresses'
    instance_count_maximum = 10


class BorrowerPreviousEmploymentsView(BorrowerResourcesMixin):
    """
    Base view of borrower employment history.
    """

    serializer_class = EmploymentV1Serializer
    model = EmploymentV1
    m2m_rel_attr = 'previous_employment'
    instance_count_maximum = 10

    # pylint: disable=no-self-use
    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def address(self, request, *args, **kwargs):
        """
        Endpoint-property, address of employment object.
        """

        view = CommonAddressView
        view.filters = {'employmentv1_address': kwargs['pk']}
        view.related_set_attr = 'employmentv1_address'
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)

    # pylint: disable=no-self-use
    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def company_address(self, request, *args, **kwargs):
        """
        Endpoint-property, company address of employment object.
        """

        view = CommonAddressView
        view.filters = {'employmentv1_company_address': kwargs['pk']}
        view.related_set_attr = 'employmentv1_company_address'
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)


class BorrowerHoldingAssetsView(HoldingAssetsOwnershipMixin, BorrowerResourcesMixin):
    """
    Base view of borrower holding assets.
    """

    serializer_class = HoldingAssetV1Serializer
    model = HoldingAssetV1
    m2m_rel_attr = 'holding_assets'

    # pylint: disable=no-self-use
    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def institution_address(self, request, *args, **kwargs):
        """
        Endpoint-property, institution address of holding asset object.
        """

        view = CommonAddressView
        view.filters = {'holdingassetv1_institution_address': kwargs['pk']}
        view.related_set_attr = 'holdingassetv1_institution_address'
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)


class BorrowerVehicleAssetsView(BorrowerResourcesMixin):
    """
    Base view of borrower vehicle assets.
    """

    serializer_class = VehicleAssetV1Serializer
    model = VehicleAssetV1
    m2m_rel_attr = 'vehicle_assets'


class BorrowerInsuranceAssetsView(BorrowerResourcesMixin):
    """
    Base view of borrower insurance assets.
    """

    serializer_class = InsuranceAssetV1Serializer
    model = InsuranceAssetV1
    m2m_rel_attr = 'insurance_assets'


class BorrowerIncomesView(RestrictIncomesKindCreation, BorrowerResourcesMixin):
    """
    Base view of borrower incomes.
    """

    serializer_class = IncomeV1Serializer
    model = IncomeV1
    m2m_rel_attr = 'income'


class BorrowerExpensesView(RestrictKindCreation, BorrowerResourcesMixin):
    """
    Base view of borrower expenses.
    """

    serializer_class = ExpenseV1Serializer
    model = ExpenseV1
    m2m_rel_attr = 'expense'


class BorrowerLiabilitiesView(LiabilitiesRestrictionMixin, BorrowerResourcesMixin):
    """
    Base view of borrower liabilities.
    """

    serializer_class = LiabilityV1Serializer
    model = LiabilityV1
    m2m_rel_attr = 'liabilities'


# Coborrower

class AdvisorLoanProfileV1CoborrowerV1View(AdvisorLoanProfileV1BorrowerBaseView):
    """
    Base borrower view.
    """

    serializer_class = CoborrowerV1Serializer
    model = CoborrowerV1

    properties_mapping = {
        'address': 'coborrowerv1_address',
        'mailing_address': 'coborrowerv1_mailing_address',
        'demographics': 'coborrowerv1',
        'employment': 'coborrowerv1_employment',
        'realtor': 'coborrowerv1_realtor',
    }

    @staticmethod
    def _create_coborrower(borrower_id, serializer_instance):
        try:
            borrower = BorrowerV1.objects.get(id=borrower_id)
        except BorrowerV1.DoesNotExist:
            raise Http404('Borrower with id "{}" does not exist'.format(borrower_id))
        else:
            return serializer_instance.save(borrower=borrower)

    @staticmethod
    def _restore_coborrower(coborrower_obj, serializer_instance):
        coborrower_obj.is_active = True
        coborrower_obj.save()
        serializer_instance.instance = coborrower_obj
        return coborrower_obj

    def perform_create(self, serializer):
        borrower_id = self.kwargs['borrower']
        try:
            coborrower_obj = CoborrowerV1.objects.get(
                borrower_id=borrower_id
            )
        except CoborrowerV1.DoesNotExist:
            return self._create_coborrower(
                borrower_id=borrower_id,
                serializer_instance=serializer,
            )
        else:
            return self._restore_coborrower(
                coborrower_obj=coborrower_obj,
                serializer_instance=serializer,
            )


class CoborrowerPreviousAddressesView(CoborrowerResourcesMixin):
    """
    Base view of coborrower previous addresses.
    """

    serializer_class = AddressV1Serializer
    model = AddressV1
    m2m_rel_attr = 'previous_addresses'
    instance_count_maximum = 10


class CoborrowerPreviousEmploymentsView(CoborrowerResourcesMixin):
    """
    Base view of borrower employment history.
    """

    serializer_class = EmploymentV1Serializer
    model = EmploymentV1
    m2m_rel_attr = 'previous_employment'
    instance_count_maximum = 10

    # pylint: disable=no-self-use
    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def address(self, request, *args, **kwargs):
        """
        Endpoint-property, address of employment object.
        """

        view = CommonAddressView
        view.filters = {'employmentv1_address': kwargs['pk']}
        view.related_set_attr = 'employmentv1_address'
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)

    # pylint: disable=no-self-use
    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def company_address(self, request, *args, **kwargs):
        """
        Endpoint-property, company address of employment object.
        """

        view = CommonAddressView
        view.filters = {'employmentv1_company_address': kwargs['pk']}
        view.related_set_attr = 'employmentv1_company_address'
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)


class CoborrowerHoldingAssetsView(HoldingAssetsOwnershipMixin, CoborrowerResourcesMixin):
    """
    Base view of coborrower holding assets.
    """

    serializer_class = HoldingAssetV1Serializer
    model = HoldingAssetV1
    m2m_rel_attr = 'holding_assets'

    # pylint: disable=no-self-use
    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def institution_address(self, request, *args, **kwargs):
        """
        Endpoint-property, institution address of holding asset object.
        """

        view = CommonAddressView
        view.filters = {'holdingassetv1_institution_address': kwargs['pk']}
        view.related_set_attr = 'holdingassetv1_institution_address'
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)


class CoborrowerVehicleAssetsView(CoborrowerResourcesMixin):
    """
    Base view of coborrower vehicle assets.
    """

    serializer_class = VehicleAssetV1Serializer
    model = VehicleAssetV1
    m2m_rel_attr = 'vehicle_assets'


class CoborrowerInsuranceAssetsView(CoborrowerResourcesMixin):
    """
    Base view of coborrower insurance assets.
    """

    serializer_class = InsuranceAssetV1Serializer
    model = InsuranceAssetV1
    m2m_rel_attr = 'insurance_assets'


class CoborrowerIncomesView(RestrictIncomesKindCreation, CoborrowerResourcesMixin):
    """
    Base view of coborrower incomes.
    """

    serializer_class = IncomeV1Serializer
    model = IncomeV1
    m2m_rel_attr = 'income'


class CoborrowerExpensesView(RestrictKindCreation, CoborrowerResourcesMixin):
    """
    Base view of coborrower expenses.
    """

    serializer_class = ExpenseV1Serializer
    model = ExpenseV1
    m2m_rel_attr = 'expense'


class CoborrowerLiabilitiesView(LiabilitiesRestrictionMixin, CoborrowerResourcesMixin):
    """
    Base view of borrower liabilities.
    """

    serializer_class = LiabilityV1Serializer
    model = LiabilityV1
    m2m_rel_attr = 'liabilities'
