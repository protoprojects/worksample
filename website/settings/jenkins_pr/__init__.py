
# pylint: disable=wildcard-import
from website.settings.common import *
from website.settings.jenkins import *
from website.settings.utils import get_env_variable


current_dir_path = os.path.dirname(os.path.abspath(__file__))
TEST_RUNNER = 'core.sampletest.sampleTestRunner'
TEST_APPLICATIONS_ENABLED = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': get_env_variable('sample_CI_PR_DB_NAME'),
        'USER': get_env_variable('sample_CI_PR_DB_USERNAME'),
        'PASSWORD': get_env_variable('sample_CI_PR_DB_PASSWORD'),
        'HOST': get_env_variable('sample_CI_PR_DB_HOST'),
        'PORT': get_env_variable('sample_CI_PR_DB_PORT'),
        'ATOMIC_REQUESTS': True
    }
}

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

# Consumer Portal document uploads staged here for virus checking:
FILE_UPLOAD_TEMP_DIR = get_env_variable('DJANGO_FILE_UPLOAD_TEMP_DIR')

# Salesforce
SALESFORCE['USER'] = get_env_variable('SF_AUTH_USER')
SALESFORCE['PASSWORD'] = get_env_variable('SF_AUTH_PASS')
SALESFORCE['TOKEN'] = get_env_variable('SF_AUTH_TOKEN')
SALESFORCE['URL'] = get_env_variable('SF_AUTH_URL')
