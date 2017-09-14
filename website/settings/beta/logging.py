LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': 'sample_APP sample_DEFAULT: %(message)s %(pathname)s:%(lineno)d %(process)d:%(thread)d',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
        'fileformat': {
            'format': 'sample_APP sample_FILE: %(message)s %(pathname)s:%(lineno)d %(process)d:%(thread)d',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': ('/dev/log'),
            'formatter': 'standard',
        },
        'file_sample': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': ('/dev/log'),
            'formatter': 'fileformat',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True
        },
        'default_local': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/dj-default.txt',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 50,
            'formatter': 'standard',
        },
        'file_local_sample': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/dj-sample.txt',
            'maxBytes': 1024 * 1024,
            'backupCount': 50,
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'default_local'],
            'level': 'INFO',
            'propagate': True,
        },
        'sample': {
            'handlers': ['file_sample', 'file_local_sample'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
