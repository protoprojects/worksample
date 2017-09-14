# -*- coding: utf-8 -*-
import datetime

from dateutil.tz import tzutc
from django.db import transaction
from django.db import models
from django_postgres_pgpfields.fields import NullBooleanPGPPublicKeyField
from rest_framework import serializers

from core.fields import MaskedField, SsnDashedField

from loans.models import (
    LoanProfileV1, BorrowerV1, CoborrowerV1, AddressV1, EmploymentV1,
    HoldingAssetV1, VehicleAssetV1, InsuranceAssetV1, IncomeV1, ExpenseV1,
    ContactV1, DemographicsV1, LiabilityV1,
)
from mismo_credit.models import (
    CreditReportScore, CreditReportSummary, CreditRequestResponse,
)

from mismo_aus.models import AusRequestResponse

from advisor_portal.serializers.fields import (
    NullableEmailField, NullableCharField,
)


class AdvisorModelSerializer(serializers.ModelSerializer):
    """
    Customized to handle some fields
    in the way we need this.
    """
AdvisorModelSerializer.serializer_field_mapping[NullBooleanPGPPublicKeyField] = serializers.NullBooleanField
AdvisorModelSerializer.serializer_field_mapping[models.CharField] = NullableCharField
AdvisorModelSerializer.serializer_field_mapping[models.TextField] = NullableCharField
AdvisorModelSerializer.serializer_field_mapping[models.EmailField] = NullableEmailField


class AddressV1Serializer(AdvisorModelSerializer):
    class Meta:
        model = AddressV1
        fields = '__all__'


class EmploymentV1Serializer(AdvisorModelSerializer):
    company_address = AddressV1Serializer(required=False)
    address = AddressV1Serializer(required=False)

    def to_internal_value(self, data):
        data = super(EmploymentV1Serializer, self).to_internal_value(data)
        if 'address' in data:
            data['address'] = AddressV1.objects.create(**data['address'])
        if 'company_address' in data:
            data['company_address'] = AddressV1.objects.create(**data['company_address'])
        return data

    class Meta:
        model = EmploymentV1
        fields = '__all__'


class HoldingAssetV1Serializer(AdvisorModelSerializer):
    account_number = MaskedField(required=False)
    institution_address = AddressV1Serializer(required=False)
    kind = serializers.CharField(max_length=255, required=True)

    def to_internal_value(self, data):
        data = super(HoldingAssetV1Serializer, self).to_internal_value(data)
        if 'institution_address' in data:
            data['institution_address'] = AddressV1.objects.create(**data['institution_address'])
        return data

    class Meta:
        model = HoldingAssetV1
        fields = '__all__'


class VehicleAssetV1Serializer(AdvisorModelSerializer):
    class Meta:
        model = VehicleAssetV1
        fields = '__all__'


class InsuranceAssetV1Serializer(AdvisorModelSerializer):
    class Meta:
        model = InsuranceAssetV1
        fields = '__all__'


class IncomeV1Serializer(AdvisorModelSerializer):
    class Meta:
        model = IncomeV1
        fields = '__all__'


class ExpenseV1Serializer(AdvisorModelSerializer):
    class Meta:
        model = ExpenseV1
        fields = '__all__'


class LiabilityV1Serializer(AdvisorModelSerializer):
    account_identifier = MaskedField(required=False)

    class Meta:
        model = LiabilityV1
        fields = '__all__'
        read_only_fields = ('is_editable',)

    def to_internal_value(self, data):
        retval = super(LiabilityV1Serializer, self).to_internal_value(data)
        if 'comment' in retval:
            retval['comment_updated'] = datetime.datetime.utcnow().replace(tzinfo=tzutc())
        return retval


class CreditReportScoreSerializer(AdvisorModelSerializer):
    class Meta:
        model = CreditReportScore
        fields = (
            'id',
            'borrower',
            'borrower_tru_score',
            'borrower_efx_score',
            'borrower_xpn_score',
            'coborrower_tru_score',
            'coborrower_efx_score',
            'coborrower_xpn_score')
        read_only_fields = fields

    # pylint: disable=no-self-use
    def get_queryset(self):
        return CreditReportScore.objects.filter(is_active=True)

    def to_representation(self, value):
        assert isinstance(value, CreditReportScore), '%s is not an instance of %s' % (value, CreditReportScore)
        retval = super(CreditReportScoreSerializer, self).to_representation(value)
        if not value.borrower.has_active_coborrower():
            for field in ('coborrower_tru_score', 'coborrower_efx_score', 'coborrower_xpn_score'):
                retval.pop(field, None)
        return retval


class CreditReportSummarySerializer(AdvisorModelSerializer):
    credit_report_scores = CreditReportScoreSerializer(many=True, required=False)
    pdf_url = serializers.CharField(source='get_pdf_url', read_only=True)

    class Meta:
        model = CreditReportSummary
        fields = (
            'id',
            'credit_report_identifier',
            'report_xml_document',
            'report_pdf_document',
            'pdf_url',
            'credit_report_scores')
        read_only_fields = fields

    # pylint: disable=no-self-use
    def get_queryset(self):
        return CreditReportSummary.objects.filter(is_active=True)


class CreditRequestResponseSerializer(AdvisorModelSerializer):
    credit_report_summary = CreditReportSummarySerializer(many=True, required=False)

    class Meta:
        model = CreditRequestResponse
        fields = (
            'id',
            'loan_profile',
            'credit_system',
            'request_case_id',
            'requested',
            'responded',
            'response_report_id',
            'status',
            'credit_report_summary')
        read_only_fields = fields


class AusRequestResponseSerializer(AdvisorModelSerializer):
    class Meta:
        model = AusRequestResponse
        fields = (
            'id',
            'requested',
            'recommendation',
            'responded',
            'request_case_id',
            'status',
        )
        read_only_fields = fields


class ContactV1Serializer(AdvisorModelSerializer):
    address = AddressV1Serializer(required=False)

    def to_internal_value(self, data):
        data = super(ContactV1Serializer, self).to_internal_value(data)
        if 'address' in data:
            data['address'] = AddressV1.objects.create(**data['address'])
        return data

    class Meta:
        model = ContactV1
        fields = '__all__'


class DemographicsV1Serializer(AdvisorModelSerializer):
    class Meta:
        model = DemographicsV1
        fields = '__all__'


class BorrowerV1SerializerMixin(AdvisorModelSerializer):
    ssn = SsnDashedField(required=False, allow_null=True)
    previous_addresses = AddressV1Serializer(many=True, required=False)
    previous_employment = EmploymentV1Serializer(many=True, required=False)
    holding_assets = HoldingAssetV1Serializer(many=True, required=False)
    vehicle_assets = VehicleAssetV1Serializer(many=True, required=False)
    insurance_assets = InsuranceAssetV1Serializer(many=True, required=False)
    income = IncomeV1Serializer(many=True, required=False)
    expense = ExpenseV1Serializer(many=True, required=False)
    liabilities = LiabilityV1Serializer(many=True, required=False)

    realtor = ContactV1Serializer(required=False)
    demographics = DemographicsV1Serializer(required=False)

    mailing_address = AddressV1Serializer(required=False)

    def to_internal_value(self, data):
        data = super(BorrowerV1SerializerMixin, self).to_internal_value(data)
        if 'address' in data:
            data['address'] = AddressV1.objects.create(**data['address'])
        if 'mailing_address' in data:
            data['mailing_address'] = AddressV1.objects.create(**data['mailing_address'])
        return data

    class Meta:
        model = None
        fields = '__all__'


class CoborrowerV1Serializer(BorrowerV1SerializerMixin):
    class Meta:
        model = CoborrowerV1
        fields = '__all__'
        read_only_fields = ('borrower',)


class BorrowerV1Serializer(BorrowerV1SerializerMixin):
    coborrower = CoborrowerV1Serializer(required=False)

    class Meta:
        model = BorrowerV1
        fields = '__all__'
        read_only_fields = ('loan_profile',)


class AdvisorLoanProfileV1ComplexSerializer(AdvisorModelSerializer):
    """
    A complex serializer which allows to create LoanProfile with
    Borrower and Coborrower objects and fill all data.
    """

    borrower = BorrowerV1Serializer(required=False)
    coborrower = CoborrowerV1Serializer(required=False)
    new_property_address = AddressV1Serializer(required=False)

    class Meta:
        model = LoanProfileV1
        exclude = ('advisor',)  # this must be set manually
        read_only_fields = (
            'encompass_sync_status',
        )
        depth = 1

    _borrower_rel_objects_mapping = {
        # FKs
        'realtor': ContactV1,
        'demographics': DemographicsV1,

        # M2Ms
        'previous_addresses':  AddressV1,
        'previous_employment': EmploymentV1,
        'holding_assets': HoldingAssetV1,
        'vehicle_assets': VehicleAssetV1,
        'insurance_assets': InsuranceAssetV1,
        'income': IncomeV1,
        'expense': ExpenseV1,
        'liabilities': LiabilityV1,
    }

    def to_internal_value(self, data):
        data = super(AdvisorLoanProfileV1ComplexSerializer, self).to_internal_value(data)
        if 'new_property_address' in data:
            data['new_property_address'] = AddressV1.objects.create(**data['new_property_address'])
        return data

    def validate(self, data):
        borrower = data.get('borrower')
        coborrower = data.get('coborrower')
        if coborrower and not borrower:
            raise serializers.ValidationError(
                'Both borrower and coborrower data must be provided for coborrower creation.'
            )
        return data

    def _save_borrower_data(self, loanprofile_obj, borrower_data, coborrower_data):
        """
        Used to save co(borrower) incoming data with creation of relational
        objects.
        """

        def extract_rel_data(data):
            rel_data = {}
            for collection_name, _ in self._borrower_rel_objects_mapping.items():
                if collection_name in data:
                    rel_data[collection_name] = data.pop(collection_name)
            return rel_data

        def fill_rel_data(obj, rel_data):
            for collection_name, collection_data in rel_data.items():
                model_cls = self._borrower_rel_objects_mapping[collection_name]
                if isinstance(collection_data, list):
                    for val in collection_data:
                        created_obj = model_cls.objects.create(**dict(val))
                        getattr(obj, collection_name).add(created_obj)
                else:
                    setattr(obj, collection_name, model_cls.objects.create(**dict(collection_data)))

        # need to pop relational data to separate it from common data
        borrower_rel_data = extract_rel_data(borrower_data)
        if coborrower_data:
            coborrower_rel_data = extract_rel_data(coborrower_data)

        # creating (co)borrower object
        borrower_obj = BorrowerV1.objects.create(loan_profile=loanprofile_obj, **borrower_data)
        if coborrower_data:
            coborrower_obj = CoborrowerV1.objects.create(borrower=borrower_obj, **coborrower_data)

        # filling relational data
        fill_rel_data(borrower_obj, borrower_rel_data)
        if coborrower_data:
            fill_rel_data(coborrower_obj, coborrower_rel_data)

        # save our work
        borrower_obj.save()
        if coborrower_data:
            coborrower_obj.save()

    def create(self, validated_data):
        with transaction.atomic():
            borrower_data = validated_data.pop('borrower', None)
            coborrower_data = validated_data.pop('coborrower', None)
            loan_profile_obj = LoanProfileV1.objects.create(**validated_data)
            self._save_borrower_data(loan_profile_obj, borrower_data, coborrower_data)
            loan_profile_obj.save()
            return loan_profile_obj


class LoanProfileV1Serializer(AdvisorModelSerializer):
    borrowers = BorrowerV1Serializer(many=True, required=False)
    new_property_address = AddressV1Serializer(required=False)
    credit_request_responses = CreditRequestResponseSerializer(many=True, required=False)
    aus_request_responses = AusRequestResponseSerializer(many=True, required=False)
    source = serializers.CharField(read_only=True)

    class Meta:
        model = LoanProfileV1
        exclude = ('advisor',)
        read_only_fields = (
            'is_demographics_questions_request_confirmed',
            'encompass_sync_status',
            'source',
        )
        depth = 1


class BorrowerV1SyncInProgressSerializer(AdvisorModelSerializer):
    class Meta:
        model = BorrowerV1
        fields = ('id', 'first_name', 'last_name', 'email',)


class LoanProfileV1SyncInProgressSerializer(AdvisorModelSerializer):
    borrowers = BorrowerV1SyncInProgressSerializer(many=True, required=False)

    class Meta:
        model = LoanProfileV1
        fields = ('id', 'encompass_sync_status', 'borrowers',)
