from datetime import date, timedelta

# pylint: disable=wildcard-import
from website.settings.common import *
from website.settings.utils import get_env_variable

DEBUG = False
TEMPLATE_DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': get_env_variable('sample_DB_NAME'),
        'USER': get_env_variable('sample_DB_USERNAME'),
        'PASSWORD': get_env_variable('sample_DB_PASSWORD'),
        'HOST': get_env_variable('sample_DB_HOST'),
        'PORT': get_env_variable('sample_DB_PORT'),
        'ATOMIC_REQUESTS': True,
        'OPTIONS': {
            'sslmode': 'require'
        }
    }
}

SECRET_KEY = get_env_variable('sample_SECRET_KEY')

INSTALLED_APPS += (
    "gunicorn",
    'raven.contrib.django.raven_compat',
    'storages',
)

#EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
EMAIL_BACKEND = "django_ses.SESBackend"
AWS_SES_REGION_NAME = get_env_variable('AWS_SES_REGION_NAME')
AWS_SES_REGION_ENDPOINT = get_env_variable('AWS_SES_REGION_ENDPOINT')
# ALIBI: django-ses ignores standard AWS API/boto environment variable
# AWS_DEFAULT_REGION, and also does not construct SES endpoint from region.

DEFAULT_FROM_EMAIL = 'sample QA <test.advisor1@sample.com>'

ALLOWED_HOSTS = ['qa2.sample.com']

# Loan sifter
LOAN_SIFTER_USERNAME = get_env_variable('sample_LOAN_SIFTER_USERNAME')
LOAN_SIFTER_PASSWORD = get_env_variable("sample_LOAN_SIFTER_PASSWORD")

# Sentry
RAVEN_CONFIG = {
    'dsn': 'http://a1d9efc1636e45a78bb25750642b9939:a6470a0011f04583b64a25e9233d062e@54.149.81.159/2'
}

# Rest framework. Removed authentication classes on beta server, cause
# nginx auth_basic generate 403
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = ()

SITE_PATH = 'http://qa2.sample.com'

SALT = get_env_variable('sample_SALT')

STAGE = "qa"

AWS_STORAGE_BUCKET_NAME = 'static-sample'
S3_URL = 'https://%s.s3.amazonaws.com/' % AWS_STORAGE_BUCKET_NAME
COMPRESS_URL = STATIC_URL = S3_URL
COMPRESS_STORAGE = 'core.compress_storage.CachedS3BotoStorage'
STATICFILES_STORAGE = 'core.compress_storage.CachedS3BotoStorage'

AWS_ACCESS_KEY_ID = get_env_variable("sample_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = get_env_variable("sample_AWS_SECRET_ACCESS_KEY")
AWS_QUERYSTRING_AUTH = False
AWS_IS_GZIPPED = True

AWS_HEADERS = {
    # Expires 10 years in the future at 8PM GMT
    'Expires': (date.today() + timedelta(days=365 * 10)).strftime('%a, %d %b %Y 20:00:00 GMT'),
    'Cache-Control': 'max-age=86400',
}

ADMIN_BASE_LEAD_EMAIL = "development.team@sample.com"
ADMIN_PARTNERS_LEAD_EMAIL = "development.team@sample.com"

SURVEYMONKEY_API = {
    'api_key': get_env_variable('SURVEYMONKEY_API_KEY'),
    'access_token': get_env_variable('SURVEYMONKEY_API_ACCESS_TOKEN')
}

BOX_API_OAUTH_CLIENT_ID = get_env_variable('sample_BOX_API_OAUTH_CLIENT_ID')
BOX_API_OAUTH_CLIENT_SECRET = get_env_variable(
    'sample_BOX_API_OAUTH_CLIENT_SECRET')
BOX_API_OAUTH_REDIRECT_URL = 'https://qa2.sample.com/callbacks/box/redirect'
BOX_API_OAUTH_REDIRECT_URL_SELF = 'https://qa2.sample.com/callbacks/box/redirect/self/'
BOX_API_OAUTH_TOKEN_STORE = get_env_variable(
    'sample_BOX_API_OAUTH_TOKEN_STORE')

TWILIO_ACCOUNT_SID = get_env_variable('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = get_env_variable('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = get_env_variable('TWILIO_PHONE_NUMBER')

SALESFORCE['USER'] = get_env_variable('SF_AUTH_USER')
SALESFORCE['PASSWORD'] = get_env_variable('SF_AUTH_PASS')
SALESFORCE['TOKEN'] = get_env_variable('SF_AUTH_TOKEN')
SALESFORCE['URL'] = get_env_variable('SF_AUTH_URL')

DOCUMENT_TRANSFER_CLIENT = get_env_variable('DOCUMENT_TRANSFER_CLIENT')
AWS_KMS_S3_CONSUMER_DOC_KEY = get_env_variable('AWS_KMS_S3_CONSUMER_DOC_KEY')
AWS_KMS_S3_CONSUMER_DOC_BUCKET = get_env_variable('AWS_KMS_S3_CONSUMER_DOC_BUCKET')

# Recaptcha
RECAPTCHA_ENABLED = get_env_variable('RECAPTCHA_ENABLED')
RECAPTCHA_SITE_KEY = get_env_variable('RECAPTCHA_SITE_KEY')
RECAPTCHA_SECRET_KEY = get_env_variable('RECAPTCHA_SECRET_KEY')
RECAPTCHA_VERIFICATION_URL = get_env_variable('RECAPTCHA_VERIFICATION_URL')
