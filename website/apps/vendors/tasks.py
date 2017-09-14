from celery import task

from vendors.sf_push import SalesforcePush, SalesforceLoanProfileMapper
from vendors.sf_request import SalesforceAdvisorRequest


@task
def push_lead_to_salesforce(contact_request_id):
    '''contact request -> lead'''
    sf_push = SalesforcePush(contact_request_id)
    sf_push.push()


@task
def push_loan_dict_to_salesforce(loan_profile_dict, loan_profile_id):
    '''lp-based data dictionary -> lead'''
    SalesforceLoanProfileMapper.push(loan_profile_dict, loan_profile_id)


@task
def get_advisor_for_loan_profile_salesforce(loan_profile_v1_id):
    '''get advisor for loan profile'''
    sf_request = SalesforceAdvisorRequest(loan_profile_v1_id)
    sf_request.update()
