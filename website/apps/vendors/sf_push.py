import copy
from datetime import datetime
import logging

from dateutil.tz import tzutc

from django.core.exceptions import ObjectDoesNotExist

from contacts.models import ContactRequest
from loans.models import LoanProfileV1
from vendors.serializers import sampleContactRequestSerializer, sampleLoanProfileSerializer
from vendors.sf_request import SalesforceAdvisorRequest
from vendors.sf_utils import SalesforceUtils
from vendors import models as v_models

logger = logging.getLogger("sample.vendors.sf_push")

SF_CONTACT_CRM_TYPE = 'salesforce'


class SalesforcePush(object):
    '''
    Transmit a sample ContactRequest + Optional MortgageProfile
    to salesforce as a lead
    '''

    def __init__(self, contact_request_id):
        contact_request = ContactRequest.objects.select_subclasses().get(
            id=contact_request_id)
        mortgage_profile_id = getattr(
            contact_request, 'mortgage_profile_id', False)

        # this is a singleton configured via the admin
        sf_ratequote_info = v_models.SalesforceRateQuoteInfo.get_solo()

        # map in the singletown fields to the name of the fields in SF
        # names are not identical since __ are not allowed as model names by Django
        data_map = {
            'LeadSource': sf_ratequote_info.LeadSource,  # sample Organic RateQuote
            'Lead_Source_Details__c': sf_ratequote_info.Lead_Source_Details,
            'Medium__c': sf_ratequote_info.Medium,  # no change
            'OwnerId': sf_ratequote_info.OwnerId,
            'Lead_Priority__c': sf_ratequote_info.Lead_Priority,  # Priority
            'Lead_Preferred_language__c': sf_ratequote_info.Lead_Preferred_language,
            'Pardot_Created__c': sf_ratequote_info.Pardot_Created,
        }

        context_map = copy.deepcopy(data_map)

        if mortgage_profile_id:
            context_map['typed_profile'] = SalesforceUtils.typed_mortgage_profile(contact_request.mortgage_profile)

        self.serializer = sampleContactRequestSerializer(contact_request, context=context_map)
        self.contact_request = contact_request

    def push(self):
        '''send contact to SF'''
        contact_map = self.serializer.data

        # ALIBI: serializer conflict with reserved 'type' on object
        contact_map['type'] = 'Lead'

        salesforce_client = SalesforceUtils.create_salesforce_client()
        if salesforce_client:
            try:
                response = salesforce_client.create(contact_map)
            except Exception as exc:
                logger.exception('SF-CONTACT-LEAD-PUSH FAILED')
                raise exc
            else:
                if isinstance(response, list) and len(response) == 1:
                    if 'success' in response[0].keys() and response[0]['success']:
                        logger.info(
                            'SF-CONTACT-LEAD-PUSH %s-%s, url: %s -> lead Id : %s',
                            contact_map['Lead_State__c'], contact_map['Loan_Purpose__c'],
                            salesforce_client.serverUrl, response[0]['id'])
                        self.contact_request.crm_id = response[0]['id']
                        self.contact_request.crm_type = SF_CONTACT_CRM_TYPE
                        self.contact_request.save()
                    else:
                        logger.error('SF-CONTACT-LEAD-PUSH FAILED: response[0]: %s', response[0])
                else:
                    logger.error('SF-CONTACT-LEAD-PUSH FAILED: response: %s', response)

                return response


class SalesforceLoanProfileMapper(object):
    '''
    Translate a sample LoanProfileV1 + MortgageProfile
    to data dictionary for salesforce
    '''

    def __init__(self, loan_profile):

        # this is a singleton configured via the admin
        sf_sampleone_reg_info = v_models.SalesforcesampleOneRegInfo.get_solo()

        # map in the singletown fields to the name of the fields in SF
        # names are not identical since __ are not allowed as model names by Django

        data_map = {
            'LeadSource': sf_sampleone_reg_info.LeadSource,
            'Lead_Source_Details__c': sf_sampleone_reg_info.Lead_Source_Details,
            'Medium__c': sf_sampleone_reg_info.Medium,  # no change
            'OwnerId': sf_sampleone_reg_info.OwnerId,
            'Lead_Priority__c': sf_sampleone_reg_info.Lead_Priority,  # no change
            'Lead_Preferred_language__c': sf_sampleone_reg_info.Lead_Preferred_language,
            'Pardot_Created__c': sf_sampleone_reg_info.Pardot_Created,
        }

        context_map = copy.deepcopy(data_map)
        if loan_profile.mortgage_profile:
            if loan_profile.mortgage_profile.id:
                context_map['typed_profile'] = SalesforceUtils.typed_mortgage_profile(
                    loan_profile.mortgage_profile)
        else:
            logger.error('SF-LOAN-LEAD no mortgage profile: loan %s', loan_profile.guid)

        self.serializer = sampleLoanProfileSerializer(loan_profile, context=context_map)
        self.loan_profile = loan_profile

    def translate(self):
        '''translate loan proile to SF-ready dictionary'''
        loan_map = self.serializer.data

        # ALIBI: serializer conflicts
        loan_map['type'] = 'Lead'
        if self.loan_profile.crm_id:
            loan_map['Id'] = self.loan_profile.crm_id

        logged_info = {
            'guid': loan_map['sampleID__c'],
            'Conversion Url': loan_map['Conversion_URL__c'],
            'Medium': loan_map['Medium__c'],
            'Loan Type': loan_map['type'],
            'Property State': loan_map['Lead_State__c'],
            'Loan Amount': loan_map['Loan_Amount__c'],
            'OwnerId': loan_map['OwnerId'],
            'Advisor Email': loan_map['AdvisorEmail__c'],
        }

        logger.info('LOAN-INFO-SENT-TO-SF loan info %s', logged_info)
        return loan_map

    @staticmethod
    # pylint: disable=too-many-branches
    def push(loan_profile_dict, loan_profile_id):
        salesforce_client = SalesforceUtils.create_salesforce_client()
        # pylint: disable=too-many-nested-blocks
        if salesforce_client:
            try:
                if 'Id' in loan_profile_dict:
                    # this won't happen in practice, so long as LEADs are automatically converted to OPPORTUNITIES
                    #  - this will render the Salesforce LEAD objects read-only.
                    response = salesforce_client.update(loan_profile_dict)
                else:
                    response = salesforce_client.create(loan_profile_dict)
            except Exception as exc:
                logger.exception('SF-LOAN-LEAD-PUSH FAILED %s', loan_profile_id)
                raise exc
            else:
                try:
                    loan_profile = LoanProfileV1.objects.get(id=loan_profile_id)
                except ObjectDoesNotExist as exc:
                    logger.error("SF-LOAN-LEAD_PUSH FAILED - LPv1 %d not found", loan_profile.guid)
                    raise exc

                if isinstance(response, list) and len(response) == 1:
                    if 'success' in response[0].keys() and response[0]['success']:
                        logger.info(
                            'SF-LOAN-LEAD-PUSH %s, url: %s -> lead Id : %s',
                            loan_profile.guid,
                            salesforce_client.serverUrl, response[0]['id'])
                        if not loan_profile.crm_id:
                            loan_profile.crm_id = response[0]['id']
                            loan_profile.crm_type = SF_CONTACT_CRM_TYPE
                            loan_profile.crm_last_sent = datetime.utcnow().replace(tzinfo=tzutc())
                            loan_profile.save(update_fields=['crm_id', 'crm_type', 'crm_last_sent'])
                    else:
                        logger.error('SF-LOAN-LEAD-PUSH FAILED: response[0]: %s', response[0])
                else:
                    logger.error('SF-LOAN-LEAD-PUSH FAILED: response: %s', response)

                if response and loan_profile and not loan_profile.advisor:
                    # commence transaction to get advisor for loan
                    sf_request = SalesforceAdvisorRequest(loan_profile.id)
                    sf_request.query()
        else:
            logger.error('SF-LOAN-LEAD-PUSH FAILED: no salesforce connection')
            # in the event that the salesforce client is misconfigures/unavailable, fall back
            sf_request = SalesforceAdvisorRequest(loan_profile_id)
            sf_request.assign_default(log_suffix='NO-SALESFORCE-CONNECTION')
