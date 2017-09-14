# pylint: disable=wildcard-import
from website.settings.common import *
from website.settings.utils import get_env_variable

from .auth import *
from .apps import *
from .celery_conf import *
from .glob import *
from .logging import *
from .salesforce import *
from .services import *

ADVISOR_FALLBACK_NOTIFICATION_EMAIL = 'system@sample.com'
MIDDLEWARE_CLASSES += (
    'corsheaders.middleware.CorsMiddleware',
)
CORS_ORIGIN_WHITELIST = (
    'alpha-portal-pr.sample.com',
    'alpha-portal.sample.com',
    'beta-portal.sample.com',
    'beta.sample.com',
    'beta-consumer.sample.com',
    'consumer-portal-pr.sample.com',
    'advisor.int.sample.com', # - S3  MAP instance
    'myhome.int.sample.com' # - S3 CP instance
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
CP_URL['HOST'] = 'myhome.int.sample.com'
