import os

# pylint: disable=wildcard-import
from website.settings.common import *
from website.settings.utils import get_env_variable

current_dir_path = os.path.dirname(os.path.abspath(__file__))


DEBUG = False
TEST_APPLICATIONS_ENABLED = False
TEST_RUNNER = 'core.sampletest.sampleTestRunner'

INSTALLED_APPS += (
    'django_jenkins',

    # project test apps
    'ga_proxy',
    'money',
    'money.tests.test_money_app',
)

JENKINS_TASKS = (
    # 'django_jenkins.tasks.django_tests',
    # 'django_jenkins.tasks.dir_tests',
    'django_jenkins.tasks.run_pep8',
    # 'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.run_pylint',
    # 'django_jenkins.tasks.run_jslint',
    # 'django_jenkins.tasks.run_jshint',
    # 'django_jenkins.tasks.run_csslint',
    # 'django_jenkins.tasks.run_sloccount',
    # 'django_jenkins.tasks.lettuce_tests',
)

PEP8_RCFILE = join(PROJECT_PATH, 'pep8.rc')
PYLINT_RCFILE = join(PROJECT_PATH, 'pylint.cfg')

PROJECT_APPS = (
    'accounts',
    'advisor_portal',
    'affordability',
    'box',
    'chat',
    'contacts',
    'core',
    'customer_portal',
    'encompass',
    'ga_proxy',
    'loans',
    'mismo_aus',
    'mismo_credit',
    'money',
    'money.tests.test_money_app',
    'mortgage_profiles',
    'pages',
    'vendors',
    'storage',
    'voa'
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': get_env_variable('sample_CI_DB_NAME'),
        'USER': get_env_variable('sample_CI_DB_USERNAME'),
        'PASSWORD': get_env_variable('sample_CI_DB_PASSWORD'),
        'HOST': get_env_variable('sample_CI_DB_HOST'),
        'PORT': get_env_variable('sample_CI_DB_PORT'),
        'ATOMIC_REQUESTS': True
    }
}

EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

JSHINT_CHECKED_FILES = [
    join(PROJECT_PATH, 'design/app/scripts'),
]

CELERY_ALWAYS_EAGER = True

# Environment variable value options: 'mortech' or 'loan_sifter'
RATE_QUOTE_SERVICE = get_env_variable('RATE_QUOTE_SERVICE')

# Loan sifter
LOAN_SIFTER_USERNAME = get_env_variable('sample_LOAN_SIFTER_USERNAME')
LOAN_SIFTER_PASSWORD = get_env_variable("sample_LOAN_SIFTER_PASSWORD")
LOAN_SIFTER_ENDPOINT = 'http://localhost:5000/loansifter_test'

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': join(PROJECT_PATH, 'logs', 'default.log'),
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 50,
            'formatter': 'standard',
        },
        'file_sample': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': join(PROJECT_PATH, 'logs', 'sample.log'),
            'maxBytes': 1024 * 1024,
            'backupCount': 50,
            'formatter': 'standard',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'sample': {
            'handlers': ['file_sample', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

# Ensure the tokens cache file exists
_box_tokens_file = open(current_dir_path + 'box.tokens', 'w+')
_box_tokens_file.close()
BOX_API_OAUTH_CLIENT_ID = '''7s01t8zsbuwgi1tse4hs8qdrdm5hdfba'''
BOX_API_OAUTH_CLIENT_SECRET = '''AZ8guS1Rh6W3gPcZDFhwWpRrdafnMQXM'''
BOX_API_OAUTH_REDIRECT_URL = '''http://127.0.0.1:8000/callbacks/box/redirect/'''
BOX_API_OAUTH_REDIRECT_URL_SELF = '''http://127.0.0.1:8000/callbacks/box/redirect/self/'''
BOX_API_OAUTH_TOKEN_STORE = current_dir_path + 'box.tokens'

TWILIO_ACCOUNT_SID = get_env_variable('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = get_env_variable('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = get_env_variable('TWILIO_PHONE_NUMBER')

# Salesforce
SALESFORCE['USER'] = get_env_variable('SF_AUTH_USER')
SALESFORCE['PASSWORD'] = get_env_variable('SF_AUTH_PASS')
SALESFORCE['TOKEN'] = get_env_variable('SF_AUTH_TOKEN')
SALESFORCE['URL'] = get_env_variable('SF_AUTH_URL')

ADVISOR_STORAGE_HOOK_ENABLE = False

with open(os.path.abspath(join(PROJECT_PATH, '../fieldkeys/test_public.key'))) as pubkey:
    PGPFIELDS_PUBLIC_KEY = pubkey.read()
with open(os.path.abspath(join(PROJECT_PATH, '../fieldkeys/test_private.key'))) as privkey:
    PGPFIELDS_PRIVATE_KEY = privkey.read()

# Consumer Portal document uploads staged here for virus checking:
FILE_UPLOAD_TEMP_DIR = get_env_variable('DJANGO_FILE_UPLOAD_TEMP_DIR')
AFFORDABILITY_ENDPOINT = "http://localhost:4444/affordability"
