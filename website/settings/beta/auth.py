from website.settings.utils import get_env_variable

USE_DUO_AUTH = True
DUO_SECRET = get_env_variable('sample_DUO_SECRET')
DUO_INTEGRATION_KEY = get_env_variable('sample_DUO_INTEGRATION_KEY')
DUO_API_HOST = get_env_variable('sample_DUO_API_HOST')
