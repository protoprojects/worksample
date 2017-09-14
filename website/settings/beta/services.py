from website.settings.utils import get_env_variable


ADVISOR_PORTAL_HOST = 'https://beta-portal.sample.com'

# Environment variable value options: 'mortech' or 'loan_sifter'
RATE_QUOTE_SERVICE = get_env_variable('RATE_QUOTE_SERVICE')

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

SURVEYMONKEY_API = {
    'api_key': get_env_variable('SURVEYMONKEY_API_KEY'),
    'access_token': get_env_variable('SURVEYMONKEY_API_ACCESS_TOKEN')
}

ENCOMPASS_TEST_MODE = 'False'  # String required!
ENCOMPASS_URL = get_env_variable('ENCOMPASS_URL')

SAVE_LOAN_SIFTER_RESPONSE = True
SAVE_MORTECH_RESPONSE = True

BOX_API_OAUTH_CLIENT_ID = get_env_variable('sample_BOX_API_OAUTH_CLIENT_ID')
BOX_API_OAUTH_CLIENT_SECRET = get_env_variable('sample_BOX_API_OAUTH_CLIENT_SECRET')
BOX_API_OAUTH_REDIRECT_URL = 'https://beta.sample.com/callbacks/box/redirect/'
BOX_API_OAUTH_REDIRECT_URL_SELF = 'https://beta.sample.com/callbacks/box/redirect/self/'
BOX_API_OAUTH_TOKEN_STORE = get_env_variable('sample_BOX_API_OAUTH_TOKEN_STORE')

TWILIO_ACCOUNT_SID = get_env_variable('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = get_env_variable('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = get_env_variable('TWILIO_PHONE_NUMBER')

# Google Analytics Event Proxy ENABLE, DEBUG, OFF
GA_PROXY_MODE = 'ENABLE'

ADVISOR_PORTAL_DUO_AUTH_ENABLED = get_env_variable('ADVISOR_PORTAL_DUO_AUTH_ENABLED')
ADVISOR_PORTAL_DUO_SECRET = get_env_variable('ADVISOR_PORTAL_DUO_SECRET')
ADVISOR_PORTAL_DUO_INTEGRATION_KEY = get_env_variable('ADVISOR_PORTAL_DUO_INTEGRATION_KEY')
ADVISOR_PORTAL_DUO_API_HOST = get_env_variable('ADVISOR_PORTAL_DUO_API_HOST')

ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED = get_env_variable(
    'ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED', fallback_enabled=True, fallback_value=True
)
