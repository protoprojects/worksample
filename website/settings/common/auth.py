AUTHENTICATION_BACKENDS = (
    "accounts.auth_backends.AccountsBackend",
)

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'index'
LOGIN_REDIRECT_URL = 'my-dashboard'

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
)

USE_DUO_AUTH = False
DUO_LOGIN_URL = '/admin/login/'
DUO_SECRET = None
DUO_INTEGRATION_KEY = None
DUO_API_HOST = None

RESET_PASSWORD_TOKEN_EXPIRES = 3600 * 48  # Two days
