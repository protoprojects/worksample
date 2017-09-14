from os.path import join, dirname

from website.settings.utils import PROJECT_PATH

DBBACKUP_STORAGE = 'dbbackup.storage.filesystem_storage'
DBBACKUP_FILESYSTEM_DIRECTORY = join(dirname(PROJECT_PATH), 'dbbackups')
DBBACKUP_SEND_EMAIL = False
