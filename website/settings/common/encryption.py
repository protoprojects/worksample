from os.path import join, dirname

from website.settings.utils import PROJECT_PATH


PGPFIELDS_PUBLIC_KEY = None
PGPFIELDS_PRIVATE_KEY = None
PGPFIELDS_BYPASS_FIELD_EXCEPTION_IN_MIGRATIONS = True

ENCRYPTED_FIELDS_KEYDIR = join(dirname(PROJECT_PATH), 'fieldkeys')
