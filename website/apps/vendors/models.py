from django.db import models

from solo.models import SingletonModel


# The below two singletons are editable via the admin interface


class SalesforceRateQuoteInfo(SingletonModel):
    """
    A singleton for configuring the default values to be sent to Salesforce for a
    RateQuote Lead (ie a user has recieved rates from the RateQuote and wants to speak
    to an advisor instead of registering)

    See the below two files for updating the admin views:
        website/settings/common
        website/vendors/admin
    """
    LeadSource = models.CharField(max_length=100, default='sample Organic RateQuote')
    Lead_Source_Details = models.CharField(max_length=100, default='Site')
    Medium = models.CharField(max_length=100, default='RateQuote')
    OwnerId = models.CharField(max_length=100, default='005G00000076Hs8')
    Lead_Priority = models.CharField(max_length=100, default='Priority')
    Lead_Preferred_language = models.CharField(max_length=100, default='English')
    Pardot_Created = models.CharField(max_length=100, default='True')


class SalesforcesampleOneRegInfo(SingletonModel):
    """
    A singleton for configuring the default values to be sent to Salesforce for a
    sampleOne Registration Lead (ie a user completed the RateQuote and registered)

    See the below two files for updating the admin views:
        website/settings/common
        website/vendors/admin
    """
    LeadSource = models.CharField(max_length=100, default='sample Organic sampleOne')
    Lead_Source_Details = models.CharField(max_length=100, default='Site')
    Medium = models.CharField(max_length=100, default='PreQual')
    OwnerId = models.CharField(max_length=100, default='005G00000076Hs8')
    Lead_Priority = models.CharField(max_length=100, default='Special')
    Lead_Preferred_language = models.CharField(max_length=100, default='English')
    Pardot_Created = models.CharField(max_length=100, default='True')
