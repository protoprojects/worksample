from website.settings.utils import get_env_variable


DEBUG = False
TEMPLATE_DEBUG = False
TEST_APPLICATIONS_ENABLED = True

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
    },
}

SECRET_KEY = get_env_variable('sample_SECRET_KEY')
SALT = get_env_variable('sample_SALT')

EMAIL_BACKEND = "django_ses.SESBackend"
AWS_SES_REGION_NAME = get_env_variable('AWS_SES_REGION_NAME')
AWS_SES_REGION_ENDPOINT = get_env_variable('AWS_SES_REGION_ENDPOINT')
# ALIBI: django-ses ignores standard AWS API/boto environment variable
# AWS_DEFAULT_REGION, and also does not construct SES endpoint from region.

DEFAULT_FROM_EMAIL = 'sample BETA <test.advisor1@sample.com>'

ADMIN_BASE_LEAD_EMAIL = "development.team@sample.com"
ADMIN_PARTNERS_LEAD_EMAIL = "development.team@sample.com"

SITE_PATH = 'https://beta.sample.com'
STATIC_URL = SITE_PATH + '/assets/'

ALLOWED_HOSTS = [
    '127.0.0.1',
    'alpha-portal.sample.com',
    'alpha-portal-pr.sample.com',
    'beta.sample.com',
    'beta-portal.sample.com',
    'm.beta.sample.com',
    'advisor.sample.com',
    'beta-consumer.sample.com',
    'consumer-portal-pr.sample.com',
    'sf.api.beta.sample.com',
    # Production-like, for future use:
    'api.beta.sample.com',
    'advisor.beta.sample.com',
    'myhome.beta.sample.com',
]

BLOG_URL_PATH = get_env_variable(
    'BLOG_URL_PATH', fallback_enabled=True, fallback_value='/blog/'
)


# Loan sifter
LOAN_SIFTER_USERNAME = get_env_variable('sample_LOAN_SIFTER_USERNAME')
LOAN_SIFTER_PASSWORD = get_env_variable("sample_LOAN_SIFTER_PASSWORD")

# Sentry
RAVEN_CONFIG = {
    # TODO: Remove unused dsn from sentry first.
    # 'dsn': 'http://1015e45b24ae40f2bc93ae1ddcc2cb13:9e2fde888acf411782440af2d191e686@sentry.sample.com/2',
    'dsn': 'http://4e10f25fd386451f8a26e06cc6286547:bbff644f9b3c4b979d325ce1e498c05a@sentry.sample.com/8',
}

STAGE = "beta"

with open(get_env_variable('PUBLIC_PGP_KEY_PATH')) as pubkey:
    PGPFIELDS_PUBLIC_KEY = pubkey.read()
with open(get_env_variable('PRIVATE_PGP_KEY_PATH')) as privkey:
    PGPFIELDS_PRIVATE_KEY = privkey.read()

REST_FRAMEWORK_DOCS = {
    'HIDE_DOCS': False
}

# Consumer Portal document uploads staged here for virus checking:
FILE_UPLOAD_TEMP_DIR = get_env_variable('DJANGO_FILE_UPLOAD_TEMP_DIR')

DOCUMENT_TRANSFER_CLIENT = get_env_variable('DOCUMENT_TRANSFER_CLIENT')
AWS_KMS_S3_CONSUMER_DOC_KEY = get_env_variable('AWS_KMS_S3_CONSUMER_DOC_KEY')
AWS_KMS_S3_CONSUMER_DOC_BUCKET = get_env_variable('AWS_KMS_S3_CONSUMER_DOC_BUCKET')

# NOTE: this setting will destroy existing user sessions, however it should mitigate
# cookie name collision between environments.
# Further, http://www.pindi.us/blog/migrating-cross-domain-cookies-django,
# describes middleware to migrate existing sessions if we care about this..
SESSION_COOKIE_NAME = 'int-sample-session-id'
CSRF_COOKIE_NAME = 'int-sample-csrftoken'
