import urllib
import urlparse

from django.core.files.storage import get_storage_class
from storages.backends.s3boto import S3BotoStorage


class CachedS3BotoStorage(S3BotoStorage):
    """
    S3 storage backend that saves the files locally, too.
    """
    def __init__(self, *args, **kwargs):
        super(CachedS3BotoStorage, self).__init__(*args, **kwargs)
        self.local_storage = get_storage_class("compressor.storage.CompressorFileStorage")()

    def save(self, name, content):
        non_gzipped_file_content = content.file
        name = super(CachedS3BotoStorage, self).save(name, content)
        content.file = non_gzipped_file_content
        # pylint: disable=W0212
        self.local_storage._save(name, content)
        return name

    def url(self, name):
        # https://github.com/boto/boto/issues/1477
        orig = super(CachedS3BotoStorage, self).url(name)
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(orig)
        params = urlparse.parse_qs(query)
        if 'x-amz-security-token' in params:
            del params['x-amz-security-token']
        query = urllib.urlencode(params)
        url = urlparse.urlunparse(
            (scheme, netloc, path, params, query, fragment)
        )
        if name.endswith('/') and not url.endswith('/'):
            url += '/'
        return url
