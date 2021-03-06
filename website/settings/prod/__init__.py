from datetime import date, timedelta

from celery.schedules import crontab

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
        'PORT': '5432',
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
    'corsheaders',
    'storages'
)

EMAIL_BACKEND = "django_ses.SESBackend"
AWS_SES_REGION_NAME = get_env_variable('AWS_SES_REGION_NAME')
AWS_SES_REGION_ENDPOINT = get_env_variable('AWS_SES_REGION_ENDPOINT')
# ALIBI: django-ses ignores standard AWS API/boto environment variable
# AWS_DEFAULT_REGION, and also does not construct SES endpoint from region.

DEFAULT_FROM_EMAIL = 'sample <customer.service@sample.com>'


ALLOWED_HOSTS = [
    'sample.com',  # TODO: remove after WPEngine cutover
    'www.sample.com',  # TODO: remove after WPEngine cutover
    'advisor.sample.com',
    'sf.api.sample.com',
    'cbc.api.sample.com',
    'api.sample.com',
    'box.api.sample.com',
    'task.api.sample.com',
]

# CORS setup
MIDDLEWARE_CLASSES += ('corsheaders.middleware.CorsMiddleware',)

CORS_ORIGIN_WHITELIST = (
    'myhome.sample.com',
    'www.sample.com',
    'advisor.sample.com',
)

CORS_ALLOW_CREDENTIALS = True
# Custom headers + headers specified in nginx before CORS was implemented
CORS_ALLOW_HEADERS = (
    'Accept',
    'Access-Control-Allow-Headers',
    'Authorization',
    'Cache-Control',
    'Content-Type',
    'DNT',
    'If-Modified-Since',
    'Origin',
    'Keep-Alive',
    'User-Agent',
    'X-Csrftoken',
    'X-CustomHeader',
    'X-For-Update', # used in MAP
    'X-Requested-With'
)

# Environment variable value options: 'mortech' or 'loan_sifter'
RATE_QUOTE_SERVICE = get_env_variable('RATE_QUOTE_SERVICE')

# Loan sifter
LOAN_SIFTER_USERNAME = get_env_variable('sample_LOAN_SIFTER_USERNAME')
LOAN_SIFTER_PASSWORD = get_env_variable("sample_LOAN_SIFTER_PASSWORD")

# Mortech
MORTECH_LICENSEKEY = get_env_variable('sample_MORTECH_LICENSEKEY')
MORTECH_THIRDPARTY_NAME = get_env_variable('sample_MORTECH_THIRDPARTY_NAME')
MORTECH_EMAIL = get_env_variable('sample_MORTECH_EMAIL')
MORTECH_CUSTOMER_ID = get_env_variable('sample_MORTECH_CUSTOMER_ID')

# Recaptcha
RECAPTCHA_ENABLED = get_env_variable('RECAPTCHA_ENABLED')
RECAPTCHA_SITE_KEY = get_env_variable('RECAPTCHA_SITE_KEY')
RECAPTCHA_SECRET_KEY = get_env_variable('RECAPTCHA_SECRET_KEY')
RECAPTCHA_VERIFICATION_URL = get_env_variable('RECAPTCHA_VERIFICATION_URL')

# Sentry
RAVEN_CONFIG = {
    # TODO: Remove unused dsn from sentry first.
    #'dsn': 'http://c93f8ebd3a8e45e390b31163eaaba8b5:79302be1e5a0466badf7bfc16075b8a9@sentry.sample.com/3',
    'dsn': 'http://dbbe83476873464bb48536e7a2f9b2aa:3fc265cf3897453bb7f22d95cfbc6e49@sentry.sample.com/9',
}

SITE_PATH = 'https://api.sample.com'
BLOG_URL_PATH = get_env_variable(
    'BLOG_URL_PATH', fallback_enabled=True, fallback_value='/blog/'
)

SALT = get_env_variable('sample_SALT')

STAGE = "prod"

# TODO: Separate S3 storage location for every instance
# TODO: Subfolders of prod, qa, etc. buckets, instead of distinct buckets:
# change Django and/or boto S3 URL scheme to path-style, if possible, per
# docs.aws.amazon.com/AmazonS3/latest/dev/UsingBucket.html#access-bucket-intro
AWS_STORAGE_BUCKET_NAME = get_env_variable('S3_BUCKET')
STATICFILES_STORAGE = 'core.compress_storage.CachedS3BotoStorage'
S3_URL = get_env_variable('S3_BASE_URL')
COMPRESS_URL = STATIC_URL = S3_URL
COMPRESS_STORAGE = 'core.compress_storage.CachedS3BotoStorage'

# No longer needed; retrieved automatically from environment, or instance role
# AWS_ACCESS_KEY_ID = get_env_variable("sample_AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = get_env_variable("sample_AWS_SECRET_ACCESS_KEY")

AWS_QUERYSTRING_AUTH = False
AWS_IS_GZIPPED = True

AWS_HEADERS = {
    # Expires 10 years in the future at 8PM GMT
    'Expires': (date.today() + timedelta(days=365 * 10)).strftime('%a, %d %b %Y 20:00:00 GMT'),
    'Cache-Control': 'max-age=86400',
}

ENCOMPASS_TEST_MODE = 'False'  # String required!
ENCOMPASS_URL = get_env_variable('ENCOMPASS_URL')
ENCOMPASS_EXPLICITLY_ASSIGN_ADVISOR = False

ADMIN_BASE_LEAD_EMAIL = "leads@sample.com"
ADMIN_PARTNERS_LEAD_EMAIL = "partnersleads@sample.com"

SURVEYMONKEY_API = {
    'api_key': get_env_variable('SURVEYMONKEY_API_KEY'),
    'access_token': get_env_variable('SURVEYMONKEY_API_ACCESS_TOKEN')
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': 'sample_APP sample_DEFAULT: %(message)s %(pathname)s:%(lineno)d %(process)d:%(thread)d',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
        'fileformat': {
            'format': 'sample_APP sample_FILE: %(message)s %(pathname)s:%(lineno)d %(process)d:%(thread)d',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': ('/dev/log'),
            'formatter': 'standard',
        },
        'file_sample': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': ('/dev/log'),
            'formatter': 'fileformat',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True
        }
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True,
        },
        'sample': {
            'handlers': ['file_sample'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

USE_DUO_AUTH = True
DUO_SECRET = get_env_variable('sample_DUO_SECRET')
DUO_INTEGRATION_KEY = get_env_variable('sample_DUO_INTEGRATION_KEY')
DUO_API_HOST = get_env_variable('sample_DUO_API_HOST')

BOX_API_OAUTH_CLIENT_ID = get_env_variable('sample_BOX_API_OAUTH_CLIENT_ID')
BOX_API_OAUTH_CLIENT_SECRET = get_env_variable(
    'sample_BOX_API_OAUTH_CLIENT_SECRET')
BOX_API_OAUTH_REDIRECT_URL = 'https://box.api.sample.com/callbacks/box/redirect'
BOX_API_OAUTH_REDIRECT_URL_SELF = 'https://box.api.sample.com/callbacks/box/redirect/self/'
BOX_API_OAUTH_TOKEN_STORE = get_env_variable(
    'sample_BOX_API_OAUTH_TOKEN_STORE')

TWILIO_ACCOUNT_SID = get_env_variable('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = get_env_variable('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = get_env_variable('TWILIO_PHONE_NUMBER')

# Google Analytics Event Proxy ENABLE, DEBUG, OFF
GA_PROXY_MODE = 'ENABLE'

ADVISOR_PORTAL_DUO_AUTH_ENABLED = True
ADVISOR_PORTAL_DUO_SECRET = get_env_variable('ADVISOR_PORTAL_DUO_SECRET')
ADVISOR_PORTAL_DUO_INTEGRATION_KEY = get_env_variable('ADVISOR_PORTAL_DUO_INTEGRATION_KEY')
ADVISOR_PORTAL_DUO_API_HOST = get_env_variable('ADVISOR_PORTAL_DUO_API_HOST')

ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED = get_env_variable(
    'ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED', fallback_enabled=True, fallback_value=True
)


with open(get_env_variable('PUBLIC_PGP_KEY_PATH')) as pubkey:
    PGPFIELDS_PUBLIC_KEY = pubkey.read()
with open(get_env_variable('PRIVATE_PGP_KEY_PATH')) as privkey:
    PGPFIELDS_PRIVATE_KEY = privkey.read()


BROKER_URL = get_env_variable('sample_CELERY_BROKER_URL')
if BROKER_URL.lower()[:4] == 'sqs:':
    CELERY_ENABLE_REMOTE_CONTROL = False
    CELERY_SEND_EVENTS = False
    BROKER_TRANSPORT_OPTIONS = {
        'queue_name_prefix': get_env_variable('sample_CELERY_QUEUE_NAME_PREFIX'),
        'visibility_timeout': int(get_env_variable('sample_CELERY_VISIBILITY_TIMEOUT')),
        # ALIBI: Kombu specifically requires float, or None to disable
        # TODO: General solution for env var type conversion with None option
        'polling_interval': (float(get_env_variable('sample_CELERY_POLLING_INTERVAL'))
                             if get_env_variable('sample_CELERY_POLLING_INTERVAL',
                                                 fallback_enabled=True,
                                                 fallback_value=False)
                             else None),
        # See https://github.com/celery/kombu/blob/3.0/kombu/transport/SQS.py
        'wait_time_seconds': int(get_env_variable('sample_CELERY_AWS_SQS_WAIT_TIME')),
        'region': get_env_variable('sample_CELERY_AWS_SQS_REGION'),
    }
CELERYBEAT_SCHEDULE = {
    'set_ready_to_sync_with_encompass_loan_profiles':  {
        'task': 'advisor_portal.tasks.set_ready_to_sync_with_encompass_loan_profiles',
        'schedule': crontab(minute='0', hour='20')  # every day at 20:00
    },
    'sync_all_loan_profiles_with_encompass': {
        'task': 'advisor_portal.tasks.sync_all_loan_profiles_with_encompass',
        'schedule': crontab()  # every minute
    },
    'find_stale_in_progress_loan_profiles': {
        'task': 'advisor_portal.tasks.find_stale_in_progress_loan_profiles',
        'schedule': crontab(minute='*/5')  # every 5 minutes
    },
    'run_all_aus_requests': {
        'task': 'mismo_aus.tasks.run_all_aus_requests',
        'schedule': crontab()  # every minute
    },
    'sync_unprocessed_box_events': {
        'task': 'box.tasks.SyncUnprocessedBoxEvents',
        'schedule': crontab()  # every minutes
    },
    'handle_unprocessed_uploaded_documents': {
        'task': 'storage.tasks.HandleUnprocessedUploadedDocumentsTask',
        'schedule': crontab()  # every minutes
    },
}

SALESFORCE['USER'] = get_env_variable('SF_AUTH_USER')
SALESFORCE['PASSWORD'] = get_env_variable('SF_AUTH_PASS')
SALESFORCE['TOKEN'] = get_env_variable('SF_AUTH_TOKEN')
SALESFORCE['URL'] = get_env_variable('SF_AUTH_URL')

ADVISOR_FALLBACK_NOTIFICATION_EMAIL = 'system@sample.com'

# Consumer Portal document uploads staged here for virus checking:
FILE_UPLOAD_TEMP_DIR = get_env_variable('DJANGO_FILE_UPLOAD_TEMP_DIR')

DOCUMENT_TRANSFER_CLIENT = get_env_variable('DOCUMENT_TRANSFER_CLIENT')
AWS_KMS_S3_CONSUMER_DOC_KEY = get_env_variable('AWS_KMS_S3_CONSUMER_DOC_KEY')
AWS_KMS_S3_CONSUMER_DOC_BUCKET = get_env_variable('AWS_KMS_S3_CONSUMER_DOC_BUCKET')

CP_REGISTRATION_RATE_LIMIT = get_env_variable(
    'sample_CP_REGISTRATION_RATE_LIMIT', fallback_enabled=True, fallback_value='15/d')

# NOTE: this setting will destroy existing user sessions, however it should mitigate
# cookie name collision between environments.
# Further, http://www.pindi.us/blog/migrating-cross-domain-cookies-django,
# describes middleware to migrate existing sessions if we care about this..
SESSION_COOKIE_NAME = 'sample-session-id'
CSRF_COOKIE_NAME = 'sample-csrftoken'
