import datetime


REST_FRAMEWORK_ADVISOR_PORTAL_THROTTLE = 'advisor_portal_throttle'
REST_FRAMEWORK_CUSTOMER_PORTAL_THROTTLE = 'customer_portal_throttle'
REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.serializers.HyperlinkedModelSerializer',

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'accounts.authentication.CustomWebTokenAuthentication',
    ),

    'DEFAULT_RENDERER_CLASSES': (
        'core.renderers.CamelCaseJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),

    'DEFAULT_PARSER_CLASSES': (
        'core.parsers.CamelCaseJSONParser',
        'core.parsers.CamelCaseMultiPartParser',
        'rest_framework.parsers.FormParser',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),

    'DATE_INPUT_FORMATS': ['%Y-%m-%d'],
    'COERCE_DECIMAL_TO_STRING': False,

    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',
        REST_FRAMEWORK_ADVISOR_PORTAL_THROTTLE: '10000/hour',
        REST_FRAMEWORK_CUSTOMER_PORTAL_THROTTLE: '1000/hour',
    }
}

REST_FRAMEWORK_EXTENSIONS = {
    'DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX': '',
}

JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(hours=8),
}

REST_FRAMEWORK_DOCS = {
    'HIDE_DOCS': True
}
