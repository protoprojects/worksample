from django.contrib import admin, messages
from django.conf import settings
from django.core import signing
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from pinax.notifications import models as notification
from authtools.admin import UserAdmin as AuthtoolsUserAdmin, BASE_FIELDS, ADVANCED_PERMISSION_FIELDS, DATE_FIELDS
from solo.admin import SingletonModelAdmin

from accounts.models import (User, Customer, Advisor, DefaultAdvisor, Realtor, Specialist, Coordinator,
                             PhoneVerification, CustomerProtectedProxyModel,)
from accounts.forms import AdminAdvisorForm
from core.admin import CustomModelAdmin
from core.utils import mask_email, mask_phone_number
from customer_portal.throttles import LoginThrottle, SendRealtorPrequalEmailThrottle, SendResetEmailThrottle
from customer_portal.serializers import CustomerSendPasswordResetEmailSerializer
from twilio.rest.exceptions import TwilioRestException


class CustomUserAdmin(AuthtoolsUserAdmin):
    # pylint: disable=no-self-use
    def reset_password(self, request, queryset):
        for user in queryset:
            context = {
                'token': signing.dumps(user.email, settings.SALT),
                'scheme': 'https' if request.is_secure() else 'http',
                'host': request.get_host()
            }
            notification.send([user], 'reset_password', context)
    reset_password.short_description = 'Send email to user with password reset link'

    actions = ['reset_password']


class AdvisorAdmin(CustomUserAdmin):
    form = AdminAdvisorForm
    fieldsets = (
        BASE_FIELDS,
        ADVANCED_PERMISSION_FIELDS,
        DATE_FIELDS,
        ('Advisor', {
            'fields': ('phone', 'about', 'nmls_number', 'encompass_id', 'profile_key')
        })
    )
    list_display = ('first_name', 'last_name', 'email', 'is_active', 'is_superuser',
                    'last_login', 'date_joined', 'profile_key')


class CoordinatorAdmin(CustomUserAdmin):
    form = AdminAdvisorForm
    fieldsets = (
        BASE_FIELDS,
        ADVANCED_PERMISSION_FIELDS,
        DATE_FIELDS,
        ('Coordinator', {
            'fields': ('phone', 'encompass_id')
        })
    )


class SpecialistAdmin(CustomUserAdmin):
    form = AdminAdvisorForm
    fieldsets = (
        BASE_FIELDS,
        ADVANCED_PERMISSION_FIELDS,
        DATE_FIELDS,
        ('Specialist', {
            'fields': ('phone', 'encompass_id')
        })
    )


class RealtorAdmin(CustomUserAdmin):
    form = AdminAdvisorForm
    fieldsets = (
        BASE_FIELDS,
        ADVANCED_PERMISSION_FIELDS,
        DATE_FIELDS,
        ('Realtor', {
            'fields': ('phone',)
        })
    )


class UserAdmin(CustomUserAdmin):
    fieldsets = (
        BASE_FIELDS,
        ADVANCED_PERMISSION_FIELDS,
        DATE_FIELDS,
        ('Personal', {
            'fields': ('avatar',)
        })
    )


##################
# customer admin #
##################
class CustomerAdmin(CustomModelAdmin):
    """
    Admin form for Customer.
    """
    actions = ['mark_inactive', 'mark_active', 'clear_throttles', 'send_password_reset_email']
    # LIST VIEW
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active',)
    ordering = ('-date_joined',)

    list_display = ('first_name', 'last_name', 'view_email', 'loan_profile_guid', 'is_active', 'last_login', 'date_joined')
    list_display_links = ('view_email',)

    # DETAIL VIEW
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', ('view_email', 'is_email_verified', 'email_validation'),
                       'contact_preferences', 'view_phone', 'loan_profile_guid', 'loan_profile_info',
                       'throttle_counts')}),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined',)}),
    )

    def view_email(self, obj):
        if settings.STAGE == 'prod':
            return mask_email(obj.email)
        return obj.email

    def view_phone(self, obj):
        if settings.STAGE == 'prod':
            return 'number ends with {}'.format(mask_phone_number(obj.phone))
        return obj.phone

    # CUSTOM FIELDS
    def loan_profile_guid(self, obj):  # pylint: disable=no-self-use
        if obj.current_loan_profile:
            url = reverse('admin:loans_loanprofilev1_change', args=(obj.current_loan_profile.id,))
            link = '<a href="{0}">{1}</a>'.format(url, obj.current_loan_profile.guid)
            return mark_safe(link)
        else:
            return None

    def loan_profile_info(self, obj):  # pylint: disable=no-self-use
        loan_profile = obj.current_loan_profile
        if loan_profile:
            return 'is_active: {0}\n lock_owner: {1}\n is_prequalified: {2}\n encompass: {3}'.format(
                loan_profile.is_active,
                loan_profile.lock_owner,
                loan_profile.is_prequalified(),
                loan_profile.encompass_sync_status
            )
        else:
            return None

    def throttle_counts(self, obj):  # pylint: disable=no-self-use
        return 'login: {0}\n send password reset email: {1}\n send realtor prequal email: {2}\n'.format(
            LoginThrottle.get_cache_count_for_email(obj.email),
            SendResetEmailThrottle.get_cache_count_for_email(obj.email),
            SendRealtorPrequalEmailThrottle.get_cache_count_for_email(obj.email),
        )

    # CUSTOM ACTIONS
    def clear_throttles(self, request, queryset):
        for customer in queryset:
            LoginThrottle.clear_cache_for_email(customer.email)
            SendResetEmailThrottle.clear_cache_for_email(customer.email)
            SendRealtorPrequalEmailThrottle.clear_cache_for_email(customer.email)
            self.message_user(request, 'throttles cleared for {0}'.format(customer.email), messages.SUCCESS)

    def send_password_reset_email(self, request, queryset):
        for customer in queryset:
            CustomerSendPasswordResetEmailSerializer.send_password_reset_email(customer)
            self.message_user(request, 'reset password email sent to {0}'.format(customer.email), messages.SUCCESS)


class PhoneVerificationAdmin(admin.ModelAdmin):
    actions_on_top = True
    actions_on_bottom = False
    actions = ('create_sms', 'create_call',)
    list_display = readonly_fields = ('phone', 'code', 'email', 'user', 'is_verified', 'created', 'updated',)

    def has_add_permission(self, request):
        return False

    def create_sms(self, request, queryset):
        """
        Custom action Create Sms
        """
        for verification_obj in queryset:
            self.send_code(request, verification_obj, PhoneVerification.VERIFICATION_METHOD_CHOICES.sms)

    def create_call(self, request, queryset):
        """
        Custom action Create Call
        """
        for verification_obj in queryset:
            self.send_code(request, verification_obj, PhoneVerification.VERIFICATION_METHOD_CHOICES.call)

    def send_code(self, request, verification_obj, method):
        """
        Sends code to phone number from verification_obj via twilio service

        :param request: HttpRequest instance
        :param verification_obj: PhoneVerification instance
        :param method: choice from PhoneVerification.VERIFICATION_METHOD_CHOICES
        :return: None
        """
        try:
            verification_obj.send_code(method)
        except TwilioRestException:
            msg = 'Sending verification code failed for phone number {}.'.format(
                  verification_obj.phone)
            self.message_user(request, msg, messages.WARNING)
        else:
            msg = 'Phone verification code for phone number {} will be delivered by {}'.format(
                  verification_obj.phone, method.capitalize())
            self.message_user(request, msg, messages.SUCCESS)


admin.site.register(CustomerProtectedProxyModel, CustomerAdmin)
admin.site.register(Advisor, AdvisorAdmin)
admin.site.register(DefaultAdvisor, SingletonModelAdmin)
admin.site.register(Coordinator, CoordinatorAdmin)
admin.site.register(Specialist, SpecialistAdmin)
admin.site.register(Realtor, RealtorAdmin)
admin.site.register(User, UserAdmin)

# Register PhoneVerificationAdmin only for testing stages
if settings.STAGE in ('qa', 'beta', 'dev',):
    admin.site.register(PhoneVerification, PhoneVerificationAdmin)
