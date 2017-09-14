import logging

from django.conf import settings
from pinax.notifications import models as notification

from accounts.models import Advisor, DefaultAdvisor, User
from loans.models import LoanProfileV1
from vendors.sf_utils import SalesforceUtils

logger = logging.getLogger("sample.vendors.sf_request")


class SalesforceAdvisorRequest(object):
    '''
    Given a loan profile previously sync'd to Salesforce
    Request an advisor assignment, associate with loan profile
    '''

    def __init__(self, loan_profile_v1_id):
        loan_profile = LoanProfileV1.objects.get(id=loan_profile_v1_id)
        # if crm_id not set, or if crm_type != SF_CONTACT_CRM_TYPE throw something
        self.loan_profile = loan_profile

    def query(self):
        salesforce_client = SalesforceUtils.create_salesforce_client()
        if salesforce_client:
            if self.loan_profile.crm_id:
                query = ("SELECT Owner.Email, ConvertedOpportunityId FROM Lead "
                         "WHERE Id='{0}'".format(self.loan_profile.crm_id))
                try:
                    response = salesforce_client.query(query)
                except Exception:
                    logger.exception('SF-LOAN-LEAD-ASSIGNMENT-QUERY FAILED')
                    raise
                else:
                    owner_email = self._extract_advisor_email(response)
                    if owner_email:
                        logger.info(
                            'SF-LOAN-LEAD-ASSIGNMENT %s, url: %s -> Loan Id : %s',
                            owner_email, salesforce_client.serverUrl, self.loan_profile.guid)
                        advisors = Advisor.objects.filter(email=owner_email)
                        if 0 < advisors.count():
                            self.loan_profile.advisor = advisors.first()
                            self.loan_profile.save(update_fields=['advisor'])
                            if 1 < advisors.count():
                                logger.error('SF-ADVISOR-REQUEST-MULTIPLE-MATCHES for %s (%d)',
                                             owner_email, advisors.count())
                        elif 0 == advisors.count():
                            logger.error('SF-ADVISOR-REQUEST-NO-MATCH for %s: received %s',
                                         self.loan_profile.guid, owner_email)
                            self.assign_default(log_suffix='NO-ADVISOR-MATCH')
                    else:
                        logger.error('SF-LOAN-LEAD-ASSIGNMENT FAILED: empty advisor email for %s: %s',
                                     self.loan_profile.guid, response)
                        self.assign_default(log_suffix='LEAD-ASSIGNMENT-FAILED')

                    opportunity_id = self._extract_opp_id(response)
                    if opportunity_id:
                        logger.info(
                            'SF-LOAN-OPP-UPDATE %s, url: %s -> Loan Id : %s',
                            opportunity_id, salesforce_client.serverUrl, self.loan_profile.guid)
                        self.loan_profile.crm_id = opportunity_id
                        self.loan_profile.crm_object_type = LoanProfileV1.CRM_OBJECT_TYPE_CHOICES.opportunity
                        self.loan_profile.save(update_fields=['crm_id', 'crm_object_type'])
                    else:
                        logger.warning('SF-LOAN-OPP-UPDATE FAILED: empty opp ID for %s: %s',
                                       self.loan_profile.guid, response)

            else:
                self.assign_default(log_suffix='NO-CRM-ID')

            if self.loan_profile.advisor:
                if not self.loan_profile.storage_id or not self.loan_profile.storage.storage_id:
                    self.loan_profile.create_storage()

    @staticmethod
    def _extract_advisor_email(salesforce_results):
        if len(salesforce_results):
            resp = salesforce_results[0]
            owner = resp.get('Owner')
            if owner:
                owner_email = owner.get('Email')
                if owner_email:
                    return owner_email
        return None

    @staticmethod
    def _extract_opp_id(salesforce_results):
        if len(salesforce_results):
            resp = salesforce_results[0]
            opp = resp.get('ConvertedOpportunityId')
            if opp:
                return opp
        return None

    def assign_default(self, log_suffix):
        '''
        assign the default advisor
        a unique log_suffix must be entered whenever this funciton is called to ensure that
        there is a unique log_slug.  Otherwise, it will be ambigous as to what cause the
        default advisor to be assigned
        '''
        default_advisor = DefaultAdvisor.get_solo().default_advisor
        if default_advisor:
            logger.warning('SF-ADVISOR-REQUEST-DEFAULT%s for %s: setting to %s',
                           log_suffix, self.loan_profile.guid, default_advisor.email)
            self.loan_profile.advisor = default_advisor
            self.loan_profile.save(update_fields=['advisor'])

            if not self.loan_profile.storage_id or not self.loan_profile.storage.storage_id:
                self.loan_profile.create_storage()

            context = {
                "loan_profile": self.loan_profile
            }
            fallback = User.objects.get(email=settings.ADVISOR_FALLBACK_NOTIFICATION_EMAIL)
            notification.send([self.loan_profile.advisor], "advisor_assignment", context)
            notification.send([fallback], "advisor_request_fallback", context)
        else:
            logger.error('SF-NO-DEFAULT-ADVISOR-SET-IN-DJANGO-ADMIN')
