import logging

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin.utils import unquote
from django.http import HttpResponseRedirect

from box import api_v1 as box_api
from core.admin import CustomModelAdmin, MaskFieldsMixin
from core.utils import mask_email, mask_phone_number, mask_digits, mask_currency_value
from loans.models import (LoanV1, LoanProfileV1, BorrowerV1, CoborrowerV1, EmploymentV1, AddressV1,
                          ContactV1, LiabilityV1, HoldingAssetV1, IncomeV1, ExpenseV1,
                          DemographicsV1, VehicleAssetV1, InsuranceAssetV1)
from .forms import LoanProfileV1AdminForm


logger = logging.getLogger('sample.loans.admin')


class sampleTeamV1Admin(admin.ModelAdmin):
    list_display = ('loan', 'advisor', 'coordinator', 'specialist', 'realtor', 'processor', 'escrow_officer',
                    'title_officer')


class LoanProfileV1Admin(CustomModelAdmin):
    actions = ['mark_inactive', 'mark_active', 'create_storage_action']
    form = LoanProfileV1AdminForm

    # LIST VIEW
    search_fields = ('guid',)
    list_filter = ('is_active', 'advisor')
    ordering = ('-created',)
    list_editable = ('advisor',)
    list_display = (
        'guid', 'advisor', 'customer_link', 'storage_link', 'is_active', 'is_prequalified', 'los_guid', 'crm_id',
        'crm_object_type', 'created', 'updated', 'encompass_sync_status'
    )
    list_display_links = ('guid',)

    # DETAIL VIEW
    fieldsets = (
        (None, {
            'fields': (
                'guid',
                'advisor',
                'advisor_link',
                'customer_link',
                'base_loan_amount',
                'property_value_estimated',
                'down_payment_amount',
                'purpose_of_loan',
                'loan_purpose',
                'property_purpose',
                'storage',
                'lead',
                'is_active',
                'is_already_in_contract',
                'lock_owner',
                'is_refinancing_current_address',
                'refinance_amount_of_existing_liens',
                'subject_property_address',
                'new_property_address',
                'other_on_loan',
            )}),
        ('Related Objects', {
            'fields': (
                'borrower_link',
                'primary_coborrower',
                'current_mortgage_profile',
                'selected_rate_quote_lender',
            )}),
        ('Credit', {
            'fields': (
                'find_valid_credit_report_summary',
                'valid_credit_request',
                'valid_credit_report_score',
            )}),
        ('RESPA', {
            'fields': ('respa_triggered', 'respa_triggered_at', 'respa_criteria_for_consumer_portal',)}),
        ('Encompass', {
            'fields': ('los_name', 'los_guid', 'datetime_sent_to_encompass', 'datetime_synced_with_encompass',
                       'encompass_sync_status')}),
    )

    # CUSTOM FIELDS
    def advisor_link(self, obj):  # pylint: disable=no-self-use
        if obj.advisor:
            uri = reverse('admin:accounts_advisor_change', args=(obj.advisor.id,))
            link = '<a href="{0}">{1}</a>'.format(uri, obj.advisor)
            return mark_safe(link)
        else:
            return None

    def customer_link(self, obj):  # pylint: disable=no-self-use
        if obj.customer:
            uri = reverse('admin:accounts_customerprotectedproxymodel_change', args=(obj.customer.id,))
            link = '<a href="{0}">{1}</a>'.format(uri, obj.customer)
            return mark_safe(link)
        else:
            return None

    def borrower_link(self, obj):  # pylint: disable=no-self-use
        if obj.primary_borrower:
            uri = reverse('admin:loans_borrowerv1_change', args=(obj.primary_borrower.id,))
            link = '<a href="{0}">{1}</a>'.format(uri, obj.primary_borrower)
            return mark_safe(link)
        else:
            return None

    def storage_link(self, obj):  # pylint: disable=no-self-use
        if obj.has_storage:
            uri = reverse('admin:storage_storage_change', args=(obj.storage.id,))
            link = '<a href="{0}">{1}</a>'.format(uri, obj.storage.storage_id)
            return mark_safe(link)
        else:
            return None

    # CUSTOM ACTIONS
    def get_urls(self):
        urls = super(LoanProfileV1Admin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name  # pylint: disable=protected-access
        custom_urls = [
            url(r'^(.+)/create_storage/$', self.admin_site.admin_view(self.create_storage_view),
                name='%s_%s_create_storage' % info),
        ]
        return custom_urls + urls

    def create_storage_view(self, request, object_id):
        instance = self.get_object(request, unquote(object_id))
        self.create_storage(request, instance)

        info = self.model._meta.app_label, self.model._meta.model_name  # pylint: disable=protected-access
        post_url = reverse('admin:%s_%s_change' % info, current_app=self.admin_site.name, args=(instance.id,))
        return HttpResponseRedirect(post_url)

    def create_storage_action(self, request, queryset):
        for loan_profile in queryset:
            self.create_storage(request, loan_profile)

    def create_storage(self, request, loan_profile):
        try:
            loan_profile.create_storage()
            if loan_profile.storage_id:
                self.message_user(request, 'Storage was successfully created.', messages.SUCCESS)
            else:
                msg = 'Storage creation failed. All criteria must be true.  criteria: {0}'.format(
                    loan_profile._create_storage_criteria())  # pylint: disable=protected-access
                self.message_user(request, msg, messages.WARNING)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception('Error on storage creation for LoanProfileV1 #%s - %s', loan_profile.id, e)
            self.message_user(request, 'Storage creation failed.', messages.WARNING)

    # pylint: disable=super-on-old-class
    def get_changelist_form(self, request, **kwargs):
        # this override that the form specified in self.form is used when editing multiple loan_profiles
        # in the admin list view
        kwargs.setdefault('form', self.form)
        return super(LoanProfileV1Admin, self).get_changelist_form(request, **kwargs)

    # pylint: disable=no-self-use
    def save_model(self, request, obj, form, change):
        if 'advisor' in form.changed_data:
            box_api.loan_profile_folder_add_advisor(obj, obj.advisor)
        obj.save()


class LoanV1Admin(CustomModelAdmin):
    list_display = ('loan_id', 'is_active', 'property_address', 'last_sync')


class EmploymentAdmin(CustomModelAdmin):
    list_display = ('company_name',)


class AddressAdmin(CustomModelAdmin):
    list_display = ('street', 'city', 'state', 'postal_code')


class ContactAdmin(MaskFieldsMixin, CustomModelAdmin):
    mask_fields = ['email', 'phone']
    list_display = ('first_name', 'last_name', 'company_name', 'address', 'email')

    def view_email(self, obj):
        if settings.STAGE == 'prod' and obj.email:
            return mask_email(obj.email)
        return obj.email

    def view_phone(self, obj):
        if settings.STAGE == 'prod':
            return 'number ends with {}'.format(mask_phone_number(obj.phone))
        return obj.phone


class BorrowerMaskFieldsMixin(MaskFieldsMixin):
    mask_fields = ['email', 'home_phone', 'ssn', 'income', 'expense', 'holding_assets', 'dob', 'insurance_assets']

    def view_email(self, obj):
        if settings.STAGE == 'prod' and obj.email:
            return mask_email(obj.email)
        return obj.email

    def view_home_phone(self, obj):
        if settings.STAGE == 'prod':
            return 'number ends with {}'.format(mask_phone_number(obj.home_phone))
        return obj.home_phone

    def view_ssn(self, obj):
        if settings.STAGE == 'prod':
            return mask_digits(str(obj.ssn))
        return obj.ssn

    def view_income(self, obj):
        incomes_str = ''
        for i in obj.income.all():
            incomes_str += ' {}'.format(i)
        if settings.STAGE == 'prod':
            return mask_currency_value(incomes_str)
        return incomes_str

    def view_expense(self, obj):
        expense_str = ''
        for i in obj.expense.all():
            expense_str += ' {}'.format(i)
        if settings.STAGE == 'prod':
            return mask_currency_value(expense_str)
        return expense_str

    def view_dob(self, obj):
        dob = obj.dob.strftime('%m/%d/%Y')
        if settings.STAGE == 'prod':
            return mask_digits(dob)
        return dob

    def view_holding_assets(self, obj):
        holding_assets_str = ''
        for i in obj.holding_assets.all():
            holding_assets_str += ' {}'.format(i)
        if settings.STAGE == 'prod':
            return mask_currency_value(holding_assets_str)
        return holding_assets_str

    def view_insurance_assets(self, obj):
        insurance_assets_str = ''
        for i in obj.insurance_assets.all():
            insurance_assets_str += ' {}'.format(i)
        if settings.STAGE == 'prod':
            return mask_currency_value(insurance_assets_str)
        return insurance_assets_str


class BorrowerAdmin(BorrowerMaskFieldsMixin, CustomModelAdmin):
    list_display = ('is_active', 'first_name', 'last_name', 'middle_name', 'email',)


class CoborrowerAdmin(BorrowerMaskFieldsMixin, CustomModelAdmin):
    list_display = ('is_active', 'first_name', 'last_name', 'middle_name', 'email')


class HoldingAssetAdmin(MaskFieldsMixin, CustomModelAdmin):
    mask_fields = ['current_value']
    list_display = ('name', 'quantity', 'symbol', 'cusip', 'kind', 'current_value', 'institution_name',
                    'institution_address')

    def view_current_value(self, obj):
        if settings.STAGE == 'prod':
            return mask_currency_value(str(obj.current_value))
        return obj.current_value


class MaskValueFieldMixin(MaskFieldsMixin):
    mask_fields = ['value']

    def view_value(self, obj):
        if settings.STAGE == 'prod':
            return mask_currency_value(str(obj.value))
        return obj.value


class LiabilityAdmin(CustomModelAdmin):
    list_display = ('kind', 'source', 'holder_name', 'monthly_payment', 'months_remaining',
                    'unpaid_balance', 'exclude_from_liabilities', 'will_be_paid_off',
                    'will_be_subordinated', 'comment')


class VehicleAssetAdmin(MaskValueFieldMixin, CustomModelAdmin):
    list_display = ('make', 'model', 'year', 'value')


class InsuranceAssetAdmin(MaskValueFieldMixin, CustomModelAdmin):
    list_display = ('kind', 'name', 'value')


class IncomeAdmin(MaskValueFieldMixin, CustomModelAdmin):
    list_display = ('kind', 'name', 'value', 'description', 'use_automated_process')


class ExpenseAdmin(MaskValueFieldMixin, CustomModelAdmin):
    list_display = ('kind', 'name', 'value', 'description')


class DemographicsAdmin(CustomModelAdmin):
    list_display = ('ethnicity', 'race', 'gender', 'is_us_citizen')

admin.site.register(LoanV1, LoanV1Admin)
admin.site.register(LoanProfileV1, LoanProfileV1Admin)
admin.site.register(EmploymentV1, EmploymentAdmin)
admin.site.register(AddressV1, AddressAdmin)
admin.site.register(ContactV1, ContactAdmin)
admin.site.register(BorrowerV1, BorrowerAdmin)
admin.site.register(CoborrowerV1, CoborrowerAdmin)
admin.site.register(HoldingAssetV1, HoldingAssetAdmin)
admin.site.register(VehicleAssetV1, VehicleAssetAdmin)
admin.site.register(LiabilityV1, LiabilityAdmin)
admin.site.register(InsuranceAssetV1, InsuranceAssetAdmin)
admin.site.register(IncomeV1, IncomeAdmin)
admin.site.register(ExpenseV1, ExpenseAdmin)
admin.site.register(DemographicsV1, DemographicsAdmin)
