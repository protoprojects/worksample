from website.settings.common import INSTALLED_APPS

INSTALLED_APPS += (
    "gunicorn",
    'raven.contrib.django.raven_compat',
    'storages',
    # django CORS middleware
    'corsheaders',

    'rest_framework_docs',

    # project test apps
    'website.apps.money.tests.test_money_app',
)
