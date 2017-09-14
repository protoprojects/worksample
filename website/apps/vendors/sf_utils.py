import logging

import beatbox

from django.conf import settings

from mortgage_profiles.models import MortgageProfilePurchase, MortgageProfileRefinance

logger = logging.getLogger("sample.vendors.sf_utils")


class SalesforceUtils(object):
    """Utility methods for Salesforce interaction"""

    @staticmethod
    def typed_mortgage_profile(mortgage_profile):
        """Get the typed MortgageProfile subclass for an MP id"""
        if mortgage_profile:
            if mortgage_profile.kind == 'refinance':
                return MortgageProfileRefinance.objects.get(id=mortgage_profile.id)
            elif mortgage_profile.kind == 'purchase':
                return MortgageProfilePurchase.objects.get(id=mortgage_profile.id)

    @staticmethod
    def create_salesforce_client():
        """Build a beatbox Salesforce client and log in"""
        salesforce_client = beatbox.PythonClient()
        salesforce_client.serverUrl = settings.SALESFORCE['URL']
        try:
            login_response = salesforce_client.login(
                settings.SALESFORCE['USER'],
                settings.SALESFORCE['PASSWORD'] + settings.SALESFORCE['TOKEN']
            )
        except Exception:
            logger.exception('SF-LOGIN-FAILED')
            return None
        else:
            if 'sessionId' not in login_response.keys():
                logger.error('SF-LEAD-PUSH LOGIN FAILED: response: %s', login_response)
            else:
                return salesforce_client
        return None
