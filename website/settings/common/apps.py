INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # don't touch this, import order plays a role
    'suit',

    'django.contrib.humanize',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.sitemaps',

    # project
    'accounts',
    'box',
    'contacts',
    'core',
    'customer_portal',
    'mortgage_profiles',
    'pages',
    'loans',
    'affordability',
    'sample_notifications',
    'encompass',
    'storage',
    'advisor_portal',
    'chat',
    'mismo_credit',
    'mismo_aus',
    'vendors',
    'voa',

    # 3rd party
    'authtools',
    'django_extensions',
    'rest_framework',
    'pinax.notifications',
    'sorl.thumbnail',
    'compressor',
    'suit_redactor',
    'referral',
    'actstream',
    'cacheops',
    'solo',
    'django_postgres_pgpfields',
)
