import django_filters

from loans.models import LoanProfileV1


class LoanProfileInProgressFilter(django_filters.FilterSet):
    is_submitted = django_filters.CharFilter(method='filter_submitted_loans')
    is_ma_created = django_filters.BooleanFilter(name='customer', lookup_expr='isnull')

    class Meta:
        model = LoanProfileV1
        fields = ['is_submitted', 'is_ma_created', 'purpose_of_loan']

    @staticmethod
    def filter_submitted_loans(queryset, name, value):
        """
        Filter queryset by SYNCED/NEVER_SYNCED encompass flag.
        """
        if value in (True, 'True', 'true', '1'):
            return queryset.filter(encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNCED)
        else:
            return queryset.filter(encompass_sync_status=LoanProfileV1.ENCOMPASS_NEVER_SYNCED)
