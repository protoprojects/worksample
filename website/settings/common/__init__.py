# pylint: disable=wildcard-import
import sys
from os.path import join

from website.settings.utils import PROJECT_PATH

sys.path.append(PROJECT_PATH)
sys.path.append(join(PROJECT_PATH, 'apps'))

# local apps
from advisor_portal.settings import *
from customer_portal.settings import *
from mismo_credit.settings import *
from mismo_aus.settings import *
from chat.settings import *

# modules
# pylint: disable=ungrouped-imports
from .admin import *
from .apps import *
from .auth import *
from .backup import *
from .celery_conf import *
from .constants import *
from .encompass import *
from .encryption import *
from .ga import *
from .glob import *
from .i18n import *
from .logging import *
from .rest_framework import *
from .salesforce import *
from .static_and_media import *
from .testing import *
from .time import *
