# Vendors
This application is for handling external api requests from business partners or third-party integrations. It validates incoming data, stores it and sends a JSON response. Authentication is handled via certificates.
- App documentation: see documenation/vendors
- Company docs: https://sample.box.com/s/dfdpaq7z15uxropvhtj19w7o1q8nluqv

## Set Up
You will need a Salesforce account and access to the Dev Console. You can also use your tool of choice for sending POST requests to your localhost such as cURL, Postman and/or ngrok.

To create a Questionaire:
- From the Salesforce Dashboard, open an opportunity
- Click the "sample Questionaire..." button

This will send a JSON request to this application and create a LoanProfileV1. It should then open that questionnaire on the Advisor Portal dashboard for you.

#### Dev Console

Salesforce has a Dev Console for manipulating and viewing SOQL and APEX modules. It also contains logs for the requests. Requests are handled from Salesforce by the `SendOppsampleController.apxc`. This is where Opportunity data is queried and sent as a request to this application. To find it:

- File > Open
- Select Classes for Entity Type.
- Type the controller name into the Filter.

To view request logs as they are sent, make sure the Dev Console is open before you click the "sample Questionnaire" button.
To view tests for the controller, open the `sampleSendOppTestClass.apxc` file.

## Inbound Salesforce API
Handles JSON requests from Salesforce generated leads.
* Sample JSON request: See documentation/vendors

Request properties are returned snakecase. Capitalized letters become lower case and camelcase becomes snakecase.

- `OwnerId` becomes `owner_id`
- `Loan_Type__c` becomes `loan_type__c`

## Outbound Salesforce Validator (utils.py)
Inspects JSON request for data integrity. Also contains factories for loan profile creation.

## Outbound Salesforce API
Current version simply sends Rate Quote Tool directly to Salesforce
Does a loose-mapping of values from `ContactRequest` (and subclasses) and `MortgageProfile`[`Purchase`|`Refinance`] to the Salesforce `Lead` structure.

Based on the [Matt's initial work in `sample-data`] (https://github.com/sample/sample-analytics/blob/master/sfdc_push/sfdc_misc_lead_transfer.py) - notably the `sfdc_push/sfdc_misc_lead_transfer.py` transfer system.

### Required Configuration Parameters

```
SALESFORCE['USER']='sfuser'
SALESFORCE['PASSWORD']='sfpass'
SALESFORCE['TOKEN']='sftoken123456'
SALESFORCE['URL']='https://test.salesforce.com/services/Soap/u/20.0'
```

these settings are accesed in beta, qa, and production by setting the following environment variables:

```
SF_AUTH_USER
SF_AUTH_PASS
SF_AUTH_TOKEN
```

 in case salesforce assignment to an advisor should fail, provide a notification address (any email/DL) for this emergency:

```
ADVISOR_FALLBACK_NOTIFICATION_EMAIL = '<valid email!>'
```

For _development_ purposes in local installations (if you don't wish to run celeryd locally), you'll want to configure

```
CELERY_ALWAYS_EAGER = True
```
