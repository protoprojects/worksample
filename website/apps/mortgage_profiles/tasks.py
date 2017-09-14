import logging

from celery import task
from mortgage_profiles.mortech import MortechApi

logger = logging.getLogger('sample.mortgage_profiles.tasks')


@task
def refresh_rate_quote(mortgage_profile):
    """Sends new rate quote request for current mortgage profile."""
    api = MortechApi(mortgage_profile)
    api.get_response()
