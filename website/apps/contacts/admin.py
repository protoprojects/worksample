import csv
import datetime
import StringIO

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse

from core.admin import MaskFieldsMixin
from core.utils import  mask_email
from referral.models import ContactRequestReferrer
from contacts.models import (
    ContactRequest, ContactRequestMortgageProfile, ConsultationRequest, ContactRequestAboutUs,
    Location, NotificationReceiver,
    ContactRequestPartner, ContactRequestLanding, ContactRequestLandingExtended, ContactRequestMobileProfile,
    ContactRequestUnlicensedState
)


class ContactRequestReferralInline(admin.StackedInline):
    model = ContactRequestReferrer
    readonly_fields = ('referrer',)


class ContactRequestAdmin(MaskFieldsMixin, admin.ModelAdmin):
    mask_fields = ['user']
    inlines = (ContactRequestReferralInline,)
    readonly_fields = ("kind", "user", "session_id")
    list_display = (
        "name_with_link", "kind", "user", "created", 'advisor', "advisor_email", "last_sync"
    )
    list_filter = (
        "kind", 'advisor', "advisor_email", "created"
    )
    download_filename = "contact-request-leads.csv"

    def __init__(self, *args, **kwargs):
        super(ContactRequestAdmin, self).__init__(*args, **kwargs)

    def get_queryset(self, request):
        qs = super(ContactRequestAdmin, self).get_queryset(request)
        return qs.select_subclasses()

    def has_add_permission(self, request):
        """
        Remove ability to add contact requests through admin interface.

        """
        return False

    # pylint: disable=no-self-use
    def name_with_link(self, obj):
        return u'<a href="%s">%s %s</a>' % (obj.get_admin_link(), obj.first_name, obj.last_name)
    name_with_link.allow_tags = True
    name_with_link.admin_order_field = "last_name"
    name_with_link.short_description = "Name"

    @staticmethod
    def format_datetime_for_excel(datetime_obj):
        return datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def escape_unicode_to_ascii(unicode_str):
        return unicode_str.encode('ascii', 'replace')

    def format_for_csv_export(self, v):
        if isinstance(v, datetime.datetime):
            v = self.format_datetime_for_excel(v)
        if isinstance(v, unicode):
            v = self.escape_unicode_to_ascii(v)
        return v

    def download_csv(self, request, queryset):
        f = StringIO.StringIO()
        writer = csv.writer(f)
        headers = queryset[0].__dict__.keys()
        writer.writerow(headers)
        for lead in queryset:
            row = [self.format_for_csv_export(v) for v in lead.__dict__.values()]
            writer.writerow(row)
        f.seek(0)

        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}'.format(self.download_filename)
        return response
    download_csv.short_description = 'Download selected as CSV'

    def view_user(self, obj):
        if settings.STAGE == 'prod' and obj.user:
            user_str = '{} {}'.format(obj.user.username, mask_email(obj.user.email))
            return user_str
        return obj.user


class ContactRequestChildMixin(object):
    def get_queryset(self, request):
        """
        Use normal queryset for contact request childs.

        """
        # pylint: disable=bad-super-call
        return super(admin.ModelAdmin, self).get_queryset(request)


class ContactRequestEmailAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    readonly_fields = ("first_name", "last_name", "kind", "user", "email", "subject", "message")


class ContactRequestMortgageProfileAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    readonly_fields = (
        "kind", "user", "mortgage_profile", "session_id"
    )

    fieldsets = (
        ('Lead info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'session_id', "mortgage_profile"
            )
        }),

        ('Advisor info', {
            'fields': (
                'is_answered', 'kind', 'advisor', 'advisor_email', 'disposition',
            )
        })
    )
    actions = ['download_csv_rate_quote_request']
    download_filename = "rate-quote-leads.csv"

    def get_values(self, lead, attrs):
        values = [self.format_for_csv_export(getattr(lead, attr, ''))
                  for attr in attrs]
        return values

    def download_csv_rate_quote_request(self, request, queryset):
        # pylint: disable=protected-access
        contact_request_headers = ContactRequestMortgageProfile._meta.get_all_field_names()
        mortgage_profile_headers = ['contactrequestmobileprofile', 'contactrequestmortgageprofile', 'created',
                                    'credit_rating', 'id', 'is_veteran', 'kind', 'loan', 'loan_id', 'ownership_time',
                                    'property_city', 'property_county', 'property_state', 'property_type',
                                    'property_zipcode', 'updated']
        purchase_headers = ['purchase_type', 'target_value', 'purchase_timing', 'purchase_down_payment']
        refinance_headers = ['cashout_amount', 'property_occupation', 'mortgage_start_date', 'purpose',
                             'property_value', 'mortgage_rate', 'mortgage_owe', 'mortgage_term',
                             'mortgage_monthly_payment']
        headers = contact_request_headers + mortgage_profile_headers + refinance_headers + purchase_headers
        f = StringIO.StringIO()
        writer = csv.writer(f)
        writer.writerow(headers)
        for lead in queryset:
            row = []
            row.extend(self.get_values(lead, contact_request_headers))

            mp = lead.mortgage_profile
            if mp:
                row.extend(self.get_values(mp, mortgage_profile_headers))
            else:
                row.extend(['' for _ in mortgage_profile_headers])
            if mp and mp.kind == u'refinance':
                row.extend(self.get_values(mp.mortgageprofilerefinance, refinance_headers))
            else:
                row.extend(['' for _ in refinance_headers])
            if mp and mp.kind == u'purchase':
                row.extend(self.get_values(mp.mortgageprofilepurchase, purchase_headers))
            else:
                row.extend(['' for _ in purchase_headers])

            writer.writerow(row)
        f.seek(0)
        response = HttpResponse(f, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}'.format(self.download_filename)
        return response
    download_csv_rate_quote_request.short_description = "Download selected as CSV"


class ConsultationRequestAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    fieldsets = (
        ('Lead info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'mortgage_profile_kind', 'mortgage_timing',
                'preferred_time', 'session_id'
            )
        }),

        ('Advisor info', {
            'fields': (
                'is_answered', 'kind', 'advisor', 'advisor_email', 'disposition',
            )
        })
    )


class ContactRequestPartnerAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    readonly_fields = ("kind", "user", "session_id")

    fieldsets = (
        ('Lead info', {
            'fields': ('first_name', 'last_name', 'email', 'session_id')
        }),

        ('Advisor info', {
            'fields': (
                'is_answered', 'kind', 'advisor', 'advisor_email', 'disposition',
            )
        })
    )
    actions = ['download_csv']
    download_filename = "partner-leads.csv"


class ContactRequestAboutUsAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    fieldsets = (
        ('Lead info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'message', 'session_id'
            )
        }),

        ('Advisor info', {
            'fields': (
                'is_answered', 'kind', 'advisor', 'advisor_email', 'disposition',
            )
        })
    )
    actions = ['download_csv']
    download_filename = "about-us-leads.csv"


class ContactRequestLandingAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    fieldsets = (
        ('Lead info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'mortgage_profile_kind', 'mortgage_timing',
                'preferred_time', 'session_id'
            )
        }),

        ('Advisor info', {
            'fields': (
                'is_answered', 'kind', 'advisor', 'advisor_email', 'disposition',
            )
        })
    )
    actions = ['download_csv']
    download_filename = "landing-leads.csv"


class ContactRequestLandingExtendedAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    fieldsets = (
        ('Lead info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'mortgage_profile_kind', 'property_zipcode',
                'property_state', 'property_county', 'is_veteran', 'credit_rating', 'ownership_time',
                'annual_income_amount', 'monthly_debt',
                'purchase_timing', 'purchase_type', 'purchase_property_value', 'purchase_down_payment',
                'refinance_purpose', 'refinance_cashout_amount', 'refinance_property_value',
                'refinance_mortgage_balance',
            )
        }),

        ('Advisor info', {
            'fields': (
                'is_answered', 'kind', 'advisor', 'advisor_email', 'disposition',
            )
        })
    )
    actions = ['download_csv']
    download_filename = "landing-extended-leads.csv"


class ContactRequestMobileProfileAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    fieldsets = (
        ('Lead info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'mortgage_profile_kind', 'credit_rating',
                'annual_income_amount', 'monthly_housing_expense', 'monthly_nonhousing_expense',
                'down_payment_amount', 'steps_progress',
            )
        }),

        ('Advisor info', {
            'fields': (
                'is_answered', 'kind', 'advisor', 'advisor_email', 'disposition',
            )
        })
    )
    actions = ['download_csv']


class ContactRequestUnlicensedStateAdmin(ContactRequestChildMixin, ContactRequestAdmin):
    fieldsets = (
        ('Lead info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'unlicensed_state_code'
            )
        }),
    )
    actions = ['download_csv']


class LocationAdmin(admin.ModelAdmin):
    list_display = ('zipcode', 'county', 'state')


class NotificationReceiverAdmin(admin.ModelAdmin):
    list_display = ('email', 'encompass_user_id', 'is_active')


admin.site.register(ContactRequest, ContactRequestAdmin)
admin.site.register(ContactRequestMortgageProfile, ContactRequestMortgageProfileAdmin)
admin.site.register(ConsultationRequest, ConsultationRequestAdmin)
admin.site.register(ContactRequestAboutUs, ContactRequestAboutUsAdmin)
admin.site.register(ContactRequestPartner, ContactRequestPartnerAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(NotificationReceiver, NotificationReceiverAdmin)
admin.site.register(ContactRequestLanding, ContactRequestLandingAdmin)
admin.site.register(ContactRequestLandingExtended, ContactRequestLandingExtendedAdmin)
admin.site.register(ContactRequestMobileProfile, ContactRequestMobileProfileAdmin)
admin.site.register(ContactRequestUnlicensedState, ContactRequestUnlicensedStateAdmin)
