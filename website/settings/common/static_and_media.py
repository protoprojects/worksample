"""
sample Static Assets
====================

sample Core does not host static files for the website with one exception:

    * `MEDIA_ROOT` - Uploads and document thumbnails
    * `STATIC_ROOT` - Django Admin style and vendor styles/scripts (Duo, etc)

Media
=====

We store thumbnail images on the server in the media/documents/thumbnails/ folder.
"""
from os.path import join

from website.settings.utils import PROJECT_PATH

# TODO: Create default images for thumbnails by file type to avoid images of PII.
MEDIA_ROOT = join(PROJECT_PATH, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/assets/admin/'

STATIC_ROOT = join(PROJECT_PATH, 'assets')
STATIC_URL = '/assets/'

STATICFILES_DIRS = (
    join(PROJECT_PATH, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
