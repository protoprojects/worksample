# Log Dictionary

## Advisor Portal Messages
___
__Slug:__ `ADVISOR-JWT-LAST-LOGIN-FAILED-TO-UPDATE`

__Message:__ ``

__Cause:__ Unable to update `last_login` field in the database

__Severity:__ Medium. Advisor can still login, but `last_login` is out of date
___
__Slug:__ `LOS-GUID-REQUEST-SYNC-BAD-STATUS`

__Message:__ `<loan profile guid>`

__Cause:__ Loan Profile is not in a sync-able state (possibly in midst of a sync)

__Severity:__ High/Low. Depends whether it continues and the loan has not synced
___
__Slug:__ `LOS-GUID-PREFLIGHT-WARNINGS`

__Message:__ `<loan profile guid> [preflight warnings]`

__Cause:__ The loan profile failed to pass pre-sync checks usually due to the MA not filling out required fields. Indicates the UI is not up-to-date with pre-flight issues

__Severity:__ Medium
___
__Slug:__ `ENCOMPASS-SYNC-LOAN-PROFILE-NOT-FOUND`

__Message:__ `<loan profile guid>`

__Cause:__ Loan Profile not found in database during sync task even
though the sync task runs from the database information

__Severity:__ Unknown/Weird
___
__Slug:__ `ENCOMPASS-SYNC-BEGIN-LOAN-PROFILE`

__Message:__ `<loan profile guid>`

__Cause:__ Start of loan profile sync to encompass. Useful for
tracking the outcome message.

__Severity:__ Low
___
__Slug:__ `ENCOMPASS-SYNC-SET-IN-PROGRESS-FLAG`

__Message:__ `<loan profile guid>`

__Cause:__ Updated loan profile sync state in database. Part of normal operation.

__Severity:__ Low
___
__Slug:__ `ENCOMPASS-SYNC-FAILED`

__Message:__ `<loan profile guid> <error message>`

__Cause:__ Failed to sync loan profile to encompass. Maybe encompass is down or has updated minimum required fields for loan sync

__Severity:__ High.
___
__Slug:__ `ENCOMPASS-SYNC-SUCCESSFUL`

__Message:__ `<loan profile guid>`

__Cause:__ Normal (and, ideally, frequent) occurence. For operational tracking of the system.

__Severity:__None
___
__Slug:__ `ENCOMPASS-SYNC-STALE-LOAN-PROFILES`

__Message:__ `[loan profile guids]`

__Cause:__ Loan profiles which have been in `SYNC_IN_PROGRESS` and were last sent to encompass more than 5 minutes ago. Something is amiss with the sync (maybe encompass is down).

__Severity:__ High

## Internal Application Issues:
___
__Slug:__ `CP-ACCOUNTS-EMAIL-VERIFIED`

__Message:__ `lp <guid> customer <guid>`

__Cause:__ Borrower has clicked "YES" in the verify-email email

__Severity:__ None/Successful; just useful to track
___
__Slug:__ `CP-ACCOUNTS-EMAIL-VERIFICATION-FAILED`

__Message:__ `code <cev code>`

__Cause:__ Borrower has clicked "YES" in the verify-email email but code was not found or used

__Severity:__ Low/Not Significant in most cases.
___
__Slug:__ `CP-ACCOUNTS-EMAIL-REPUDIATED`

__Message:__ `lp <guid> code <cev code>`

__Cause:__ Borrower has clicked "NO" in the verify-email email

__Severity:__ None/Successful; just useful to track
___
__Slug:__ `CP-ACCOUNTS-EMAIL-REPUDIATION-FAILED`

__Message:__ `code <cev code>`

__Cause:__ Borrower has clicked "NO" in the verify-email email but code was not found or used

__Severity:__ Low/Not Significant in most cases.
___
__Slug:__ `CP-COBORROWER-EMAIL-DECLINED`

__Message:__ `lp <guid>`

__Cause:__ Coborrower has clicked "NO" in the permission-to-pull-credit email

__Severity:__ None/Successful; just useful to track
___
__Slug:__ `CP-COBORROWER-EMAIL-VERIFICATION-FAILED`

__Message:__ `code <cev code>`

__Cause:__ Someone tries to use a used verification code.

__Severity:__ Low/Not Significant
___
__Slug:__ `CP-COBORROWER-VERIFY-NO-EMAIL`

__Message:__ `cob <Cobrorrower ID>`

__Cause:__ Borrower clicks "let's get personal," but the coborrower email hasn't been saved.

__Severity:__ Medium
___
__Slug:__ `CP-COBORROWER-VERIFY-WITH-EXISTING-CEV`

__Message:__ `cob <Cobrorrower ID>`

__Cause:__ Attempt to send duplicate Coborrower verification email, while existing active invitation is present. Borrower clicks "let's get personal," but the invitation is already sent.

__Severity:__ Medium
___
__Slug:__ `CP-COBORROWER-IS-ALREADY-CUSTOMER-ON-OTHER-LOAN`

__Message:__ `guid <guid of current lp> customer_id <cutomer ID who is already customer on another lp>`

__Cause:__ This implies that the current lp has a coborrower who is already the primary_borrower on another transaction.  We do not support this currently.  

__Severity:__ Low
___
__Slug:__ `CP-PASSWORD-RESET-REQUEST-FOR-INVALID-OR-INACTIVE-USER`

__Message:__ `email <email>`

__Cause:__ Attempt to reset password for user who does not exist or is set to inactive.

__Severity:__ Low
___
__Slug:__ `CP-COBORROWER-EMAIL-VERIFICATION-FAILED-NO-COB`

__Message:__ `code <cev code>`

__Cause:__ No coborrower exists for the given CustomerEmailValidation.  Could happen if a borrower's cev is passed to the coborrower endpoint.  

__Severity:__ Medium
___
__Slug:__ `CP-CUSTOMER-CREATE-PREVIOUS_ADDRESS-EXCEPTION`

__Message:__ `<Exception message>`

__Cause:__ Attempt to add a previous address for borrower or coborrower fails. No known causes.

__Severity:__ Medium
___
__Slug:__ `CP-CUSTOMER-CREATE-EMPLOYMENT-EXCEPTION`

__Message:__ `<Exception Message>`

__Cause:__ Attempt to create employment history for borrower or coborrower fails. No known causes.

__Severity:__ Medium
___
__Slug:__ `CP-CUSTOMER-CREATE-COBORROWER-EXCEPTION`

__Message:__ `<Exception Message>`

__Cause:__  IntegrityError on creating Coborrower.

__Severity:__ High
___
__Slug:__ `CP-CUSTOMER-CREATE-LOAN-PROFILE-EXCEPTION`

__Message:__ `<Customer ID> <Exception Message>`

__Cause:__  IntegrityError on creation of the LoanProfile in `CustomerLoanProfileV1Serializer.create`.  Could have a variety of causes as this is a complex method that creates a loan_profile, borrower, incomes, assets and demographics.  

__Severity:__ High
___
__Slug:__ `CP-RESET-PASSWORD-WITH-TOKEN`

__Message:__ `lp <guid> customer <guid>`

__Cause:__  Customer has successfully reset their password with a token from a reset password email.

__Severity:__ Info
___
__Slug:__ `CP-SEND-PASSWORD-RESET-EMAIL`

__Message:__ `lp <guid> customer <guid>`

__Cause:__  Customer has successfully sent a reset password email.

__Severity:__ Info
___
__Slug:__ `CP-REGISTRATION-COMPLETE`

__Message:__ `lp <guid> customer <guid> referrer_url <url>`

__Cause:__  Customer has successfully registered.

__Severity:__ Info
___
__Slug:__ `CP-THROTTLED-FAILURE`

__Message:__ `scope <throttle scope> key <cache key (type)> count <number of attempts>`

__Cause:__ Multiple retries on prohibited actions.

__Severity:__ Low; useful for tracking attemped exploits or implementation/deployment errors.
___
__Slug:__ `DECLARATION-L-FALSE-USAGE-PRIMARY `

__Message:__ `<loan profile guid>`

__Cause:__ Customer declared False for occupying as primary but marked
mortgage profile property usage as primary.

__Severity:__ Medium. Working as designed.
___
__Slug:__ `DEMOGRAPHICS-OBJ-HAS-MULTIPLE-BORROWERS`

__Message:__ `<demographics id>`

__Cause:__ Model integrity issue where more than one BorrowerV1 refer
to the same DemographicsV1 instance

__Severity:__ High

## 3rd Party Issues:

### Salesforce
___
__Slug:__ `VENDOR-SF-API-BUILD-PROFILE-EXCEPTION`

__Message:__ `<exception>`

__Cause:__ Creation of Lead, LoanProfileV1, Borrower, Coborrower, MortgageProfile failed during Salesforce-to-MAP Push

__Severity:__ High
___
__Slug:__ `VENDOR-SF-API-BUILD-PROFILE-UNKNOWN-KIND`

__Message:__ `<kind sent>`

__Cause:__ During Salesforce-to-MAP push, a non Purchase/Refinance "kind" was sent, interfering with MortgageProfile creation.

__Severity:__ Medium
___
__Slug:__ `SF-CONTACT-LEAD-PUSH FAILED`

__Message:__ `response: <message>` or `response[0] <message>`

__Cause:__ During initial transmission of a new Lead to Salesforce from a consumer portal *contact request*, salesforce refused the Lead parameters

__Severity:__ Low-Medium; Lead data saved in sample system, not relayed to Salesforce or assigned
___
__Slug:__ `SF-LOAN-LEAD`

__Message:__ `no mortgage profile: loan <loan profile UID>`

__Cause:__ missing MorgageProfile for the supplied *contact request*

__Severity:__ Low; Salesforce lead will be largely blank
___
__Slug:__ `SF-LOAN-LEAD-PUSH FAILED`

__Message:__ (optional) `- LPv1 <LPv1 ID> not found`, `response`, `response[0]`, or `no salesforce connection`

__Cause:__ Failure to locate related LoanProfileV1, or to successfully push to Salesforce.

__Severity:__ High; indicates (Message blank or case 1) data integrity error between Celery and Front-end server or (Message cases 2,3) Salesforce rejection of Lead. Message case 4 indicates Salesforce outage or credntials failure.
___
__Slug:__ `SF-LOAN-LEAD-ASSIGNMENT-QUERY FAILED`

__Message:__ None

__Cause:__ High-level failure to request advisor/opportunity from Lead in Salesforce from a CP LoanProfileV1

__Severity:__ Unknown; failure scenarios unclear
___
__Slug:__ `SF-ADVISOR-REQUEST-MULTIPLE-MATCHES`

__Message:__ `for <advisor email> (<#matching advisors>)`

__Cause:__ sample users table data integrity error

__Severity:__ High; should be impossible
___
__Slug:__ `SF-ADVISOR-REQUEST-NO-MATCH`

__Message:__ `for <LoanProfileV1 UID>: received <advisor email>`

__Cause:__ No advisor matched the response email address

__Severity:__ Medium; hard to repair, but indicates that an advisor is present/assignable in Salesforce but not in sample's system.
___
__Slug:__ `SF-LOAN-LEAD-ASSIGNMENT FAILED:`

__Message:__ `empty advisor email for <LoanProfileV1 UID>: <Salesforce Response>`

__Cause:__ Salesforce wasn't having it.

__Severity:__ Unknown; scenario unclear.
___
__Slug:__ `SF-LOAN-OPP-UPDATE FAILED:`

__Message:__ `empty opp ID for <LoanProfileV1 UID>: <Salesforce Reponse>`

__Cause:__ Failed to create or map Salesforce Opportunity in response to Lead.

__Severity:__ Low-Medium; Lead ID and object type will remain saved in the sample system. Indicates more serious problems on the Salesforce side.
___
__Slug:__ `SF-ADVISOR-REQUEST-DEFAULT`

__Message:__ `for <LoanProfileV1 UID>: setting to <default advisor email>`

__Cause:__ Salesforce advisor assignment failed (any number of possible reasons)

__Severity:__ Low, although this incurs reassignment overhead
___
__Slug:__ `SF-LOAN-LEAD-ASSIGNMENT-AND-FALLBACK FAILED`

__Message:__ ` - no advisor matched <configured fallback advisor email>`

__Cause:__ Misconfiguration + assignment error.

__Severity:__ High; LoanProfileV1 will need to be manually triaged and assigned.
___
__Slug:__ `SF-LOGIN-FAILED`

__Message:__ `<Exception>`

__Cause:__ Salesforce downtime or sample Salesforce credentials misconfiguration

__Severity:__ High
___
__Slug:__ `SF-LEAD-PUSH LOGIN FAILED:`

__Message:__ ` response: <Salesforce response>`

__Cause:__ No session returned during a Salesforce Login

__Severity:__ High

### Box.com
___
__Slug:__ `BOX-FILE-SAVE-CREDIT-REPORT-XML-EXCEPTION`

__Message:__ `loan_profile <UID> exc <exception>`

__Exception Values:__

 - _Message:_ Item with the same name already exists

__Cause:__ Re-running credit once credit has been successfully run.

__Severity:__ Medium
___
__Slug:__ NONE

__Message:__ `Resetting dropped connection: <host>.box.com`

__Cause:__ Token Expiration in Box integration

__Severity:__ Low
___
__Slug:__ `BOX-FILE-SAVE-CREDIT-REPORT-XML-EXCEPTION`

__Message:__ `loan_profile <uid> exc <Exception message>`

__Cause:__ Usually existing Credit Report Saved/location conflict

__Severity:__ Medium
___
__Slug:__ ``

__Message:__ ``

__Cause:__

__Severity:__
### MISMO CREDIT:
___
__Slug:__ `MISMO-CREDIT-REPORT-CANNOT-BE-RERUN`

__Message:__ NONE

__Cause:__ The consumer has attempted to re-run credit report but has been denied due to existing results.

__Severity:__ Medium - the UI should prevent the request, but the consequences are limited.
___
__Slug:__ `MISMO-CREDIT-PULL-STORAGE-SYNC-FAILURE`

__Message:__ None

__Cause:__ Box storage error on attempt to save credit pull results

__Severity:__ ???
___
__Slug:__ `MISMO-CREDIT-EXCEPTIONAL-EXCEPTION`

__Message:__ `loan_profile <id> exc <exception type/text>`

__Cause:__ Frankly this should never happened. Managed to producing once by deleting existing/assigned storage for a user from box without removing related sample Storage records.

__Severity:__ High
___
__Slug:__ `MISMO-CREDIT-PULL-SUCCESS`

__Message:__ `id <Job id>`

__Cause:__ Successful credit run

__Severity:__ None/Successful
### MISMO AUS:
Helpful links:
- https://www.fanniemae.com/singlefamily/desktop-underwriter
- https://www.fanniemae.com/singlefamily/technology-integration
- [list of error codes](https://www.fanniemae.com/content/technology_requirements/xis-do-du-error-codes.xls) that Fannie may return

___
__Slug:__ `AUS-NOT-RUN`

__Message:__ `errors: <JSON-serialized error array>`

__Cause:__ See errors array - values required for AUS run will often be absent, since not all completed applications will have all the necessary data, which is expected.  LoanProfileV1-level failure.

__Severity:__ Low/Medium depending on how critical the error items are to a successfuly loan application
___
__Slug:__ `MISMO-AUS-PULL-NO-START-NOT-READY`

__Message:__ `id <job ID> state <job state>`

__Cause:__ Job registered as not-ready

__Severity:__ Medium
___
__Slug:__ `MISMO-AUS-PULL-TIMEOUT`

__Message:__ `id <job ID>`

__Cause:__ Request to Fannie timed-out (timeout period set in apps/mismo_aus/settings.py)

__Severity:__ Medium
___
__Slug:__ `MISMO-AUS-PULL-CONNECTION-ERROR`

__Message:__ `id <job ID>`

__Cause:__ Request to Fannie failed to connect.  This should be a temporary issue, perhaps because Fannie Mae is down.  Check by attempting to run AUS a second time if the error occurs.  If AUS still has a connection error, contact John Jones at Fannie Mae (john_jones@fanniemae.com).

__Severity:__ Medium
___
__Slug:__ `MISMO-AUS-NO-CONTROL-OUTPUT`

__Message:__ `id: <job ID> status: <job status>`

__Cause:__ Response from Fannie did not contain control output.  This likely means our submission to Fannie was malformed.  Check box for files returned by Fannie.

__Severity:__ Medium
___
__Slug:__ `MISMO-AUS-TASK-COMPLETE`

__Message:__ `id: <job ID> status <job status> recommendation <approval recommendation from Fannie> criteria <the prequal_criteria> findings <list of reasons from Fannie why they responded as they did>`

__Cause:__ Result of a successful MISMO AUS pull

__Severity:__ None/Successful
___
__Slug:__ `sample_FILE: AUS-ERROR`

__Message:__ `error_code <Code> status <Error Detail Map>`

__Cause:__ FNMA Disqualified request (often mis-matched PII)

__Severity:__ Low-Medium
____
__Slug:__ `MISMO-AUS-PULL-INVALID-LOAN-APPLICATION-FORMAT`

__Message:__ `id <Report ID>`

__Cause:__ the loan_application.xml fails validation against the MISMO 2.3.1 DTD.  Check files return by Fannie and saved to box for reason.

__Severity:__ Medium

### Encompass:
___
__Slug:__ `RESPA-TRIGGERD-AND-LOAN-SYNCED-TO-ENCOMPASS loan_profile: <loan profile GUID>`

__Message:__ None

__Cause:__ Successful RESPA-triggering Encompass Sync.

__Severity:__ None/Successful
____
__Slug:__ `ENCOMPASS-API-GET-UNEXPECTED-RESPONSE-JSON-TYPE`

__Message:__ `<the class of the JSON response> url <Requested API URL>`

__Cause:__ ???

__Severity:__ High; this Encompass interaction will likely have failed
___
__Slug:__ `ENCOMPASS-API-PATCH-UNEXPECTED-STATUS-CODE`

__Message:__ `<Response Status Code> url <Requested Patch URL> content <Response Content>`

__Cause:__ Occurs with post-creation advisor assignment if Encompass
refused the assignment due to licensing/advisor registration
(Configuration permits advisor assignment be part of loan sync)

__Severity:__ Medium-to-High; This Encompass update to an existing record will likely have failed
___
__Slug:__ `ENCOMPASS-API-POST-UNEXPECTED-STATUS-CODE`

__Message:__ `<Response Status Code> url <Requested POST URL> content <Response Content>`

__Cause:__ Encompass responded to a loan sync with an unsuccessful status code

__Severity:__ High
___
__Slug:__ `ENCOMPASS-API-PUT-FAIL`

__Message:__ `code <Response Status Code> url <Requested PUT URL> msg <Message> content <Response Content>`

__Cause:__ Not currently used

__Severity:__ ???
___
__Slug:__ 'LOANS-SYNC-GET-ELAPSED`

__Message:__ `<elapsed time>s`

__Cause:__ Time to convert loan profile to dictionary for Encompass

__Severity:__ None/Successful

### MORTECH
___
__Slug:__ `MORTECH-XML-PARSE-ERROR`

__Message:__ `<Response message> data <Response content>`

__Cause:__ xmltodict module encountered a parsing error

__Severity:__ High
___
__Slug:__ `MORTECH-INVALID-RESPONSE-ERROR`

__Message:__ `MORTECH-INVALID-RESPONSE-ERROR: {'header': {'error_desc': <Mortech headers> }}`

__Cause:__ Mortech API returned no results or an error. See documentation for full list.

__Severity:__ High
___
__Slug:__ `MORTECH-SAVE-RESPONSE-FAILED`

__Message:__ `SAVE-MORTECH-RESPONSE-FAILED <IOError>`

__Cause:__ Failed to write response data to file.

__Severity:__ Low. Saving responses is a debugging feature that must be turned on in settings.
___
__Slug:__ `MORTECH-INVALID-REQUEST-ERROR`

__Message:__ `{'errors: <Response errors reporting invalid/missing data>'}`

__Cause:__ Invalid request parameters: state, insufficient data.

__Severity:__ Medium. The form shouldn't allow incomplete fields.
___
__Slug:__ `MORTECH-REQUEST-TIMEOUT`

__Message:__ `MORTECH-REQUEST-TIMEOUT: <Timeout Exception>`

__Cause:__ The request to Mortech has timed out.

__Severity:__ High
___
__Slug:__ `MORTECH-REQUEST-CONNECTIONERROR`

__Message:__ `MORTECH-REQUEST-CONNECTIONERROR: <Connection Exception>`

__Cause:__ The request to Mortech has experienced a network error.

__Severity:__ High
___
__Slug:__ `MORTECH-REQUEST-HTTPERROR`

__Message:__ `MORTECH-REQUEST-HTTPERROR: <HTTP Error>`

__Cause:__ The request to Mortech has responded with an unsuccessful HTTP status.

__Severity:__ High
___
__Slug:__ `MORTECH-REQUEST-REQUESTEXCEPTION`

__Message:__ `MORTECH-REQUEST-TIMEOUT: <Request Exception>`

__Cause:__ An exception while handling the request has occurred.

__Severity:__ High
___
__Slug:__ `PROGRAM-TYPE-AND-PRODUCT-NAME-NOT-MATCHED`

__Message:__ `PROGRAM-TYPE-AND-PRODUCT-NAME-NOT-MATCHED: <program_type product_name>`

__Cause:__ program_type or product_name from lender not matched with sample's programs. It defaults to the program_type from Mortech.

__Severity:__ Low. Our logic should be updated so program_type can be matched.

### RATE QUOTE TOOL
___
__Slug:__ `RATE-QUOTE-NOT-FOUND`

__Message:__ `{'detail': 'Not found'}`

__Cause:__ Visiting a rate quote url UUID endpoint that doesn't exist. Django Rest Framework response.

__Severity:__ Medium. Unless we've started purging old data from DB, the rate quote should be there.
___
__Slug:__ `RATE-QUOTE-CALCULATIONS-ERROR`

__Message:__ `<AssertionError>: <parameter> missing value.`

__Cause:__ The tool is trying to fetch data to send a Mortech request. The data is missing.

__Severity:__ High. This information is required by the form. This error indicates something is broken.
___
__Slug:__ `CONTACT-REQUEST-UNLICENSED-STATE-FOR-STATE-WITH-LICENSE`

__Message:__ `state_name <state_name>`

__Cause:__ The ConsumerPortal is saying we are not licensed in a state that the sample app says we are licensed in.  Check `StateLIcense`s to verify what states we are licensed in.  

__Severity:__ High.  This prevents customers from using our rate quote.

### Storage app
___
__Slug:__ `CACHE-DOCUMENT-TRANSFER-CLIENT-FETCH-DOCUMENT-ERROR`

__Message:__ `cache_key <cache_key> data is None`

__Cause:__ Failed to retrieve document contents from the temporary storage.

__Severity:__ High.  Unable to processed the downloaded file.
