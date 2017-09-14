from django.db.models import Prefetch
from django.http import Http404

from rest_framework import decorators, response, status, validators, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework_extensions.mixins import NestedViewSetMixin

from advisor_portal.permissions import AllowAdvisorPermission, ModifyOperationsPermission
from advisor_portal.serializers.loan_profile_v1 import (
    AddressV1Serializer, DemographicsV1Serializer, EmploymentV1Serializer,
    ContactV1Serializer,
)
from advisor_portal.views import CRUD_ACTIONS, ENDPOINT_PROPERTY_METHODS
from advisor_portal.views.mixins import AdvisorTokenAuthMixin
from core.permissions import InstanceCountMaximumPermission, INSTANCE_COUNT_MAXIMUM_DEFAULT
from core import utils as core_utils
from loans.models import (
    AddressV1, BorrowerV1, CoborrowerV1, ContactV1,
    DemographicsV1, EmploymentV1, LoanProfileV1,
)


class SelectForUpdateMixin(object):
    """
    Need to use it where it is needed to select
    object for update.
    """

    # pylint: disable=no-self-use
    def get_object_for_update(self, qs, filter_kwargs, for_update):
        if for_update:
            return qs.select_for_update().get(**filter_kwargs)
        else:
            return qs.get(**filter_kwargs)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in self.kwargs, "%s is not in %s" % (lookup_url_kwarg, self.kwargs)
        lookup_value = self.kwargs[lookup_url_kwarg]

        # allow use of guid to load Questionnaire in MAP
        # Why: this is to allow salesforce to create a link to the MAP
        #      using only a guid. Salesforce does not know the lp.id.
        #      eventually the use of lp.id should be replaced throughout the advisor_portal
        #      to use lp.guid, but that is for another day...
        # standard MAP url:
        #     /questionnaire/59/basic-questions
        # now this works too:
        #     /questionnaire/4e85282c-87a4-44db-ae86-7c4c29eb1daa/basic-questions
        if core_utils.is_uuid4(lookup_value):
            self.lookup_field = 'guid'

        filter_kwargs = {self.lookup_field: lookup_value}

        for_update = self.for_update()
        try:
            obj = self.get_object_for_update(queryset, filter_kwargs, for_update)
        except queryset.model.DoesNotExist:
            # pylint: disable=protected-access
            raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)
        self.check_object_permissions(self.request, obj)
        return obj

    def for_update(self):
        # pylint: disable=protected-access
        return 'HTTP_X_FOR_UPDATE' in self.request._request.META


# Property-like common views
class CommonPropertyLikeView(AdvisorTokenAuthMixin,
                             SelectForUpdateMixin,
                             viewsets.GenericViewSet,
                             viewsets.mixins.CreateModelMixin,
                             viewsets.mixins.RetrieveModelMixin,
                             viewsets.mixins.UpdateModelMixin,
                             viewsets.mixins.DestroyModelMixin,):
    """
    View, used to avoid code duplication while using as REST endpoint
    property.
    For example, if there is an endpoint `/loan-profiles/:id/new-property-address/`,
    new-property-address is a decorated by `detail_route` decorator function
    inside DRF viewset, so we need to call this common view inside this function.
    """

    ERRORS = {
        'missing_model': 'Model must be provided',
        'missing_filters': 'Filters must be provided',
        'missing_related_attr': 'Related set attribute must be provided',
        'missing_pk_name': 'PK name must be provided',
    }

    model = None
    serializer_class = None

    filters = {}
    related_set_attr = None
    pk_name = 'pk'

    def __init__(self, *args, **kwargs):
        super(CommonPropertyLikeView, self).__init__(*args, **kwargs)
        self.permission_classes = [IsAuthenticated, AllowAdvisorPermission, ModifyOperationsPermission, ]

    def filter_queryset_by_parent_filters(self, qs):
        assert self.filters, self.ERRORS['missing_filters']
        return qs.filter(**self.filters)

    def get_object_for_update(self, qs, filter_kwargs, for_update):
        if for_update:
            return qs.select_for_update().last()
        else:
            return qs.last()

    def get_queryset(self):
        assert self.model, self.ERRORS['missing_model']
        return self.filter_queryset_by_parent_filters(
            self.model.objects.all()
        )

    def perform_create(self, serializer):
        assert self.related_set_attr, self.ERRORS['missing_related_attr']
        assert self.pk_name, self.ERRORS['missing_pk_name']
        # Creating new object
        obj = serializer.save()
        # Getting the right relation manager
        manager = getattr(obj, self.related_set_attr)
        # This is an id of entity which will own created `obj`.
        related_obj_id = self.kwargs[self.pk_name]
        try:
            if self.for_update():
                manager.add(manager.model.objects.select_for_update().get(pk=related_obj_id))
            else:
                manager.add(manager.model.objects.get(pk=related_obj_id))
        except manager.model.DoesNotExist:
            # Need to delete created object to not
            # leave it without owner.
            obj.delete()
            raise Http404('Object does not exist.')
        else:
            obj.save()


class CommonAddressView(CommonPropertyLikeView):
    """
    Common address view, which may be used by different
    models, which address is related to.
    """

    model = AddressV1
    serializer_class = AddressV1Serializer

    def __init__(self, *args, **kwargs):
        super(CommonAddressView, self).__init__(**kwargs)

        class CheckAddressPermission(BasePermission):
            def has_object_permission(self, request, view, obj):
                if obj is None:
                    return False
                manager = getattr(obj, CommonAddressView.related_set_attr)
                advisor_id = request.user.id
                # For some reason isinstance is not working here
                model_name = manager.model.__name__
                if model_name == 'LoanProfileV1':
                    return manager.filter(advisor_id=advisor_id).exists()
                elif model_name == 'BorrowerV1':
                    return manager.filter(loan_profile__advisor_id=advisor_id).exists()
                elif model_name == 'CoborrowerV1':
                    return manager.filter(borrower__loan_profile__advisor_id=advisor_id).exists()
                elif model_name == 'EmploymentV1' or model_name == 'HoldingAssetV1':
                    return (
                        manager.filter(borrowerv1__loan_profile__advisor_id=advisor_id).exists() or
                        manager.filter(coborrowerv1__borrower__loan_profile__advisor_id=advisor_id).exists()
                    )
                else:
                    return False

        self.permission_classes.append(CheckAddressPermission)


class CommonDemographicsView(CommonPropertyLikeView):
    """
    Common demographics view, used by borrower and coborrower
    objects.
    """

    model = DemographicsV1
    serializer_class = DemographicsV1Serializer

    def __init__(self, *args, **kwargs):
        super(CommonDemographicsView, self).__init__(**kwargs)

        class CheckDemographicsPermission(BasePermission):
            def has_object_permission(self, request, view, obj):
                if obj is None:
                    return False
                manager = getattr(obj, CommonDemographicsView.related_set_attr)
                advisor_id = request.user.id
                model_name = manager.model.__name__
                if model_name == 'BorrowerV1':
                    return manager.filter(loan_profile__advisor_id=advisor_id).exists()
                elif model_name == 'CoborrowerV1':
                    return manager.filter(borrower__loan_profile__advisor_id=advisor_id).exists()
                else:
                    return False

        self.permission_classes.append(CheckDemographicsPermission)


class CommonEmploymentView(CommonPropertyLikeView):
    """
    Common employment view, used by borrower and coborrower
    objects.
    """

    model = EmploymentV1
    serializer_class = EmploymentV1Serializer

    def __init__(self, *args, **kwargs):
        super(CommonEmploymentView, self).__init__(**kwargs)

        class CheckEmploymentPermission(BasePermission):
            def has_object_permission(self, request, view, obj):
                if obj is None:
                    return False
                manager = getattr(obj, CommonEmploymentView.related_set_attr)
                advisor_id = request.user.id
                model_name = manager.model.__name__
                if model_name == 'BorrowerV1':
                    return manager.filter(loan_profile__advisor_id=advisor_id).exists()
                elif model_name == 'CoborrowerV1':
                    return manager.filter(borrower__loan_profile__advisor_id=advisor_id).exists()
                else:
                    return False

        self.permission_classes.append(CheckEmploymentPermission)


class CommonContactView(CommonPropertyLikeView):
    """
    Common contact view, used by borrower and coborrower
    objects.
    """

    model = ContactV1
    serializer_class = ContactV1Serializer

    def __init__(self, *args, **kwargs):
        super(CommonContactView, self).__init__(**kwargs)

        class CheckContactPermission(BasePermission):
            def has_object_permission(self, request, view, obj):
                if obj is None:
                    return False
                manager = getattr(obj, CommonContactView.related_set_attr)
                advisor_id = request.user.id
                model_name = manager.model.__name__
                if model_name == 'BorrowerV1':
                    return manager.filter(loan_profile__advisor_id=advisor_id).exists()
                elif model_name == 'CoborrowerV1':
                    return manager.filter(borrower__loan_profile__advisor_id=advisor_id).exists()
                else:
                    return False

        self.permission_classes.append(CheckContactPermission)


# Other views
class BorrowerBaseResourcesMixin(AdvisorTokenAuthMixin,
                                 SelectForUpdateMixin,
                                 NestedViewSetMixin,
                                 viewsets.GenericViewSet,
                                 viewsets.mixins.ListModelMixin,
                                 viewsets.mixins.CreateModelMixin,
                                 viewsets.mixins.UpdateModelMixin,
                                 viewsets.mixins.RetrieveModelMixin,
                                 viewsets.mixins.DestroyModelMixin,):

    """
    This is a mixin, used to implement borrower and coborrower
    resources (such as housing history). Avoids code duplication.
    """

    permission_classes = [
        IsAuthenticated, AllowAdvisorPermission, ModifyOperationsPermission,
        InstanceCountMaximumPermission]

    borrower_model = None
    # Url lookup, used to have ability to get borrower/coborrower id.
    lookup = None
    # To ensure that borrower and coborrower are active.
    is_active_filter = None

    # Override as needed
    instance_count_maximum = INSTANCE_COUNT_MAXIMUM_DEFAULT

    # Mixin users need to set it
    serializer_class = None
    model = None
    m2m_rel_attr = None

    def perform_create(self, serializer):
        instance = serializer.save()
        borrower_id = self.kwargs[self.lookup]
        try:
            borrower = self.borrower_model.objects.get(id=borrower_id)
        except self.borrower_model.DoesNotExist:
            raise Http404(
                'Borrower or coborrower with id "{}" does not exist.'.format(
                    borrower_id
                )
            )
        else:
            getattr(borrower, self.m2m_rel_attr).add(instance)
            return instance

    def get_queryset(self):
        return self.filter_queryset_by_parents_lookups(
            self.model.objects.filter(**self.is_active_filter)
        )


class BorrowerResourcesMixin(BorrowerBaseResourcesMixin):
    borrower_model = BorrowerV1
    lookup = 'borrowerv1'
    is_active_filter = {'borrowerv1__is_active': True}


class CoborrowerResourcesMixin(BorrowerBaseResourcesMixin):
    borrower_model = CoborrowerV1
    lookup = 'coborrowerv1'
    is_active_filter = {'coborrowerv1__is_active': True}


class AdvisorLoanProfileV1BorrowerBaseView(AdvisorTokenAuthMixin,
                                           SelectForUpdateMixin,
                                           NestedViewSetMixin,
                                           viewsets.GenericViewSet,
                                           viewsets.mixins.ListModelMixin,
                                           viewsets.mixins.CreateModelMixin,
                                           viewsets.mixins.UpdateModelMixin,
                                           viewsets.mixins.RetrieveModelMixin,
                                           viewsets.mixins.DestroyModelMixin,):

    """
    This is a mixin, used to implement borrower and coborrower
    base view. Avoids code duplication.
    """

    permission_classes = [IsAuthenticated, AllowAdvisorPermission, ModifyOperationsPermission, ]
    properties_mapping = {}

    serializer_class = None
    model = None

    def get_queryset(self):
        # TODO: use `.select_related()` here
        # when encrypted manager will support it.
        return self.filter_queryset_by_parents_lookups(
            self.model.objects.filter(
                is_active=True
            ).prefetch_related(
                Prefetch('previous_addresses'),
                Prefetch('previous_employment'),
                Prefetch('holding_assets'),
                Prefetch('vehicle_assets'),
                Prefetch('insurance_assets'),
                Prefetch('income'),
                Prefetch('expense'),
            )
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def mailing_address(self, request, *args, **kwargs):
        """
        Endpoint-property, mailing address of (co)borrower.
        """

        view = CommonAddressView
        view.filters = {
            self.properties_mapping['mailing_address']: kwargs['pk'],
            '%s__is_active' % self.properties_mapping['mailing_address']: True,
        }
        view.related_set_attr = self.properties_mapping['mailing_address']
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)

    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def demographics(self, request, *args, **kwargs):
        """
        Endpoint-property, demographics object of (co)borrower.
        """

        view = CommonDemographicsView
        view.filters = {
            self.properties_mapping['demographics']: kwargs['pk'],
            '%s__is_active' % self.properties_mapping['demographics']: True,
        }
        view.related_set_attr = self.properties_mapping['demographics']
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)

    @decorators.detail_route(methods=ENDPOINT_PROPERTY_METHODS)
    def realtor(self, request, *args, **kwargs):
        """
        Endpoint-property, realtor object of (co)borrower.
        """

        view = CommonContactView
        view.filters = {
            self.properties_mapping['realtor']: kwargs['pk'],
            '%s__is_active' % self.properties_mapping['realtor']: True,
        }
        view.related_set_attr = self.properties_mapping['realtor']
        return view.as_view(CRUD_ACTIONS)(request, *args, **kwargs)


class RestrictKindCreation(object):
    """
    Helper used to avoid creation object
    with the same kind if it already exists.
    """

    allowed_kinds = []

    def create(self, request, *args, **kwargs):
        if 'kind' in request.data:
            kind = self.request.data['kind']
            if ((kind.lower() not in self.allowed_kinds) and
                    self.get_queryset().filter(kind=kind).exists()):
                return response.Response(
                    data={'detail': 'Item with kind \'{}\' already exists.'.format(kind)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return super(RestrictKindCreation, self).create(request, *args, **kwargs)


class RestrictIncomesKindCreation(RestrictKindCreation):
    """
    Helper used to avoid creation incomes
    with the same kind if it already exists
    except 'Other' incomes
    """

    allowed_kinds = ['other']


class HoldingAssetsOwnershipMixin(object):
    @staticmethod
    def _change_asset_owner(instance, data, loan_profile_id):
        """
        Method should return boolean which indicates was ownership
        transferred or not, and message if needed.
        """
        borrower_id = data.get('borrower_id')
        coborrower_id = data.get('coborrower_id')
        if not borrower_id and not coborrower_id:
            return False, 'borrowerId or coborrowerId should be provided'

        lp = LoanProfileV1.objects.get(id=loan_profile_id)
        lp_borrower = lp.borrowers.first()
        if borrower_id and (lp_borrower.id != borrower_id):
            return False, 'Can only transfer ownership within current loan profile.'
        if hasattr(lp_borrower, 'coborrower') and coborrower_id and lp_borrower.coborrower.id != coborrower_id:
            return False, 'Can only transfer ownership within current loan profile.'

        instance.borrowerv1.clear()
        instance.coborrowerv1.clear()
        if borrower_id:
            instance.borrowerv1.add(borrower_id)
        if coborrower_id:
            instance.coborrowerv1.add(coborrower_id)
        instance.save()
        return True, None

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # PATCH should be performed as usual
        if partial:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return response.Response(serializer.data)
        # PUT should only change an owner of instance
        else:
            changed, message = self._change_asset_owner(
                instance=instance,
                data=request.data,
                loan_profile_id=(kwargs.get('borrowerv1__loan_profile') or
                                 kwargs.get('coborrowerv1__borrower__loan_profile'))
            )
            if not changed:
                return response.Response(status=status.HTTP_400_BAD_REQUEST, data={'error': message})
            return response.Response(status=status.HTTP_204_NO_CONTENT)


class LiabilitiesRestrictionMixin(HoldingAssetsOwnershipMixin):
    # Fields that are allowed for changing if
    # `is_editable` flag is set to `false`.
    allowed_to_change_fields = [
        'comment',
        'will_be_paid_off',
        'will_be_subordinated',
        'exclude_from_liabilities',
    ]

    def perform_update(self, serializer):
        instance = self.get_object()
        if not instance.is_editable:
            not_allowed_keys = []
            for key in self.request.data:
                if key == 'id':
                    if self.request.data['id'] != instance.id:
                        not_allowed_keys.append(key)
                elif key not in self.allowed_to_change_fields:
                    not_allowed_keys.append(key)
            if not_allowed_keys:
                raise validators.ValidationError(
                    "Liability entry is not editable. "
                    "Can not change following fields: {0}.".format(", ".join(not_allowed_keys))
                )
        serializer.save()
