from os.path import join

from website.settings.utils import PROJECT_PATH

DEBUG = True

ALLOWED_HOSTS = []
INTERNAL_IPS = ('127.0.0.1',)
SITE_PATH = 'https://sample.com'

BLOG_URL_PATH = '/blog/'

ADMINS = []
MANAGERS = ADMINS

SITE_ID = 1

SECRET_KEY = 'oad8s!9w63#_!19+4j63uyqsmv#^z%(*ie_k*1-^1_j&^0m!r('

# This will allow cookies from api.[env.]sample.com to be set in the
# browser when requesting from myhome/advisor.[env.]sample.com
# Otherwise cookie Same Origin Policy will be respected regardless of CORs settings
# NOTE: this pattern will be allowed for ANY subdomain of sample.com, we use cookie names
# to mitigate cookie collision between environments. As of 2017-05-10 the only shared environment
# is SM and MAINT
SESSION_COOKIE_DOMAIN = '.sample.com'
CSRF_COOKIE_DOMAIN = '.sample.com'

# Set a HTTP header that tells Django whether the request came in via HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'referral.middleware.ReferrerMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.views.decorators.csrf._EnsureCsrfCookie',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.ContactRequestMiddleware',
)

ROOT_URLCONF = 'urls'
WSGI_APPLICATION = 'wsgi.application'

SALT = ""
STAGE = "local"

MIGRATION_MODULES = {
    'pinax_notifications': 'migrations.pinax_notifications',
    'actstream': 'migrations.actstream',
}

CACHEOPS_REDIS = {
    'host': 'localhost',  # redis-server is on same machine
    'port': 6379,         # default redis port
    'db': 2,              # SELECT non-default redis database
                          # using separate redis db or redis instance
                          # is highly recommended
    'socket_timeout': 3,
}

CACHEOPS = {
    'contacts.location': ('just_enable', 60 * 60 * 24 * 365)
}

GZIP_CONTENT_TYPES = (
    'text/css',
    'application/javascript',
    'application/x-javascript',
    'text/javascript'
)

PINAX_NOTIFICATIONS_BACKENDS = [
    ("email", "core.notification_backends.SesAsyncEmailBackend"),
    ("message_center", "core.notification_backends.MessageCenterBackend"),
]
PINAX_NOTIFICATIONS_QUEUE_ALL = False
PINAX_NOTIFICATIONS_LANGUAGE_MODEL = None


ACTSTREAM_SETTINGS = {
    'MODELS': ('conditions.condition', 'loans.loan', 'actstream.action', 'progress.progressstep'),
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(PROJECT_PATH, 'templates'),
            join(PROJECT_PATH, 'apps/mismo_aus'),
            join(PROJECT_PATH, 'apps/customer_portal/templates'),
        ],
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                # sample
                'accounts.context_processors.active_profile',
                'core.context_processors.symantec_seal_url',
                'core.context_processors.stage',
                'core.context_processors.dnt',
                'core.context_processors.main_phone_processor',
                'core.context_processors.main_email_processor',
                'core.context_processors.base_url',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

ADVISOR_PROFILE_URL = {
    'PROTOCOL': 'https',
    'HOST': 'www.sample.com',
    'STEM': '/wp-json/wp/v2/mortgage-advisor?slug=',
}

ADVISOR_FALLBACK_NOTIFICATION_EMAIL = 'system@sample.com'

EXCEPTION_NOTIFICATION_EMAIL = 'y1o6m4w7x6c8j5y8@sample.slack.com'

SILENCED_SYSTEM_CHECKS = ['models.E006']

# File size limitation for uploaded documents, 10 Mb by default
DOCUMENT_MAX_UPLOAD_SIZE = 10485760

FILE_UPLOAD_HANDLERS = ['django.core.files.uploadhandler.TemporaryFileUploadHandler']

# AWS KMS S3 storage for uploaded docs transfer to the Celery server
# for the further processing - antivirus check, format conversion,
# upload to Box.
AWS_KMS_S3_CONSUMER_DOC_KEY = ''
AWS_KMS_S3_CONSUMER_DOC_BUCKET = ''

# Class which handles transfer of uploaded files from application server
# to Celery server for the further processing and upload to Box.
# By default, uses Django cache to store uploaded files contents.
DOCUMENT_TRANSFER_CLIENT = 'storage.utils.CacheDocumentTransferClient'

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': 'localhost:6379',
        'OPTIONS': {
            'DB': 1,
            'PASSWORD': '',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            }
        },
    },
    'celery': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': 'localhost:6379',
        'OPTIONS': {
            'DB': 2,
            'PASSWORD': '',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            }
        },
    },
}
