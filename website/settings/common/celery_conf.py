BROKER_URL = 'redis://localhost:6379/0'

CELERYBEAT_SCHEDULE = {}
# TODO: find a way to use only JSON
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
CELERY_TIME_EXPIRATION_LOCK = 60 * 5  # 5 minute
