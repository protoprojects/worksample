from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination


class SmallPagePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'


class LargePagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'


class SmallLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 10
