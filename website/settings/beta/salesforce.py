from website.settings.common import SALESFORCE
from website.settings.utils import get_env_variable

SALESFORCE['USER'] = get_env_variable('SF_AUTH_USER')
SALESFORCE['PASSWORD'] = get_env_variable('SF_AUTH_PASS')
SALESFORCE['TOKEN'] = get_env_variable('SF_AUTH_TOKEN')
SALESFORCE['URL'] = get_env_variable('SF_AUTH_URL')
