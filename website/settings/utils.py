from os.path import dirname, abspath
from os import environ

from django.core.exceptions import ImproperlyConfigured

PROJECT_PATH = dirname(dirname(abspath(__file__)))


def get_env_variable(var_name, fallback_enabled=False, fallback_value=None):
    """ Get the environment variable or return exception """
    try:
        val = environ[var_name]
    except KeyError:
        if not fallback_enabled:
            raise ImproperlyConfigured("Need to set the %s env variable." % var_name)
        return fallback_value
    if val in ['True', '1', 1]:
        val = True
    elif val in ['False', '0', 0]:
        val = False
    return val
