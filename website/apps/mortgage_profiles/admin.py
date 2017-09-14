from django.conf import settings
from django.contrib import admin

from core.admin import MaskFieldsMixin
from core.utils import mask_email
from mortgage_profiles.models import (
    RateQuoteRequest, MortgageProfile, MortgageProfilePurchase, MortgageProfileRefinance,
)


class MaskUserFieldMixin(MaskFieldsMixin):
    mask_fields = ['user']

    def view_user(self, obj):
        if settings.STAGE == 'prod' and obj.user:
            user_str = '{} {}'.format(obj.user.username, mask_email(obj.user.email))
            return user_str
        return obj.user


class MortgageProfileAdmin(MaskUserFieldMixin, admin.ModelAdmin):
    list_display = (
        "kind_with_link", "user", "property_zipcode", "property_state", "property_county", "ownership_time",
        "credit_score", "is_veteran", "created"
    )

    def __init__(self, *args, **kwargs):
        super(MortgageProfileAdmin, self).__init__(*args, **kwargs)

    def get_queryset(self, request):
        qs = super(MortgageProfileAdmin, self).get_queryset(request)
        return qs.select_subclasses()

    def has_add_permission(self, request):
        """
        Remove ability to add contact requests through admin interface.

        """
        return False

    # pylint: disable=no-self-use
    def kind_with_link(self, obj):
        return u'<a href="%s">%s</a>' % (obj.get_admin_link(), obj.get_kind_display())
    kind_with_link.allow_tags = True
    kind_with_link.admin_order_field = "kind"
    kind_with_link.short_description = "Kind"


class MortgageProfileChildMixin(object):
    def get_queryset(self, request):
        """
        Use normal queryset for contact request childs.

        """
        # pylint: disable=bad-super-call
        return super(admin.ModelAdmin, self).get_queryset(request)


class MortgageProfilePurchaseAdmin(MaskUserFieldMixin, MortgageProfileChildMixin, admin.ModelAdmin):
    list_display = (
        'purchase_timing', 'purchase_type', 'purchase_down_payment',
        'target_value', 'credit_score', 'user', 'created'
    )
    readonly_fields = ('uuid', 'user', 'selected_rate_quote_lender', 'loan_profilev1',)


class MortgageProfileRefinanceAdmin(MaskUserFieldMixin, MortgageProfileChildMixin, admin.ModelAdmin):
    list_display = (
        'purpose', 'property_type', 'property_value', 'mortgage_owe', 'property_occupation',
        'credit_score', 'user', 'created'
    )
    readonly_fields = ('uuid', 'user', 'selected_rate_quote_lender', 'loan_profilev1',)


class RateQuoteRequestAdmin(MaskUserFieldMixin, admin.ModelAdmin):
    list_filter = ('created', 'mortgage_profile__kind')
    list_display = ('uuid', 'created', 'mortgage_profile')
    list_display_links = ('uuid', 'mortgage_profile')
    readonly_fields = ('mortgage_profile', 'mortgage_profile_with_link', 'created')

    # pylint: disable=no-self-use
    def mortgage_profile_with_link(self, obj):
        mortgage_profile = obj.mortgage_profile.subclass
        return u'<a href="%s">%s</a>' % (mortgage_profile.get_admin_link(), mortgage_profile.get_kind_display())

    mortgage_profile_with_link.allow_tags = True

admin.site.register(MortgageProfilePurchase, MortgageProfilePurchaseAdmin)
admin.site.register(MortgageProfileRefinance, MortgageProfileRefinanceAdmin)
admin.site.register(MortgageProfile, MortgageProfileAdmin)
admin.site.register(RateQuoteRequest, RateQuoteRequestAdmin)
