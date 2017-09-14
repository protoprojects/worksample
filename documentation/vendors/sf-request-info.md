#Salesforce JSON request

Uses 6 models to create a questionaire from an opportunity

- 1 LoanProfileV1
- 2 MortgageProfile(Purchase/Refinance)
- 3 BorrowerV1
- 4 CoborrowerV1
- 5 AddressV1
- 6 Lead

Customer addresses belong to BorrowerV1, CoborrowerV1. Property addresses belong to LoanProfileV1 and MortgageProfile.

```py
{
    "attributes": {
        "type": "Opportunity",
        "url": "/services/data/v35.0/sobjects/Opportunity/0067A000002GYjvQAG"
    },
    "Id": "0067A000002GYjvQAG",                   # Lead.lead_id
    "Loan_Type__c": "Purchase",                   # MortgageProfile.kind, LoanProfileV1.purpose_of_loan
    "Property_Address__c": "1 Test Drive",        # MortgageProfile.property_street,
    "Property_City__c": "San Francisco",          # MortgageProfile.property_city
    "Property_State__c": "CA",                    # MortgageProfile.property_state
    "Property_Zip_Code__c": "94111",              # MortgageProfile.property_zicode
    "Property_County__c": "San Francisco",        # MortgageProfile.property_county
    "Property_type__c": "Single Family Residence", # MortgageProfile.property_type
    "Property_Value__c": 5900000.00,              # MortgageProfileRefinance.property_value
    "Down_Payment_Amt__c": 25000.00,              # MortgageProfilePurchase.purchase_down_payment
    "Loan_Amount__c": 150000.00, 
    "Property_Use__c": "Primary Home",            # MortgageProfile.property_occupation
    "Impound_Escrow__c": "Yes",
    "First_Time_Buyer__c": "",                    # BorrowerV1.is_first_time_buyer
    "Coborrower_First_Name__c": "Terry",          # CoborrowerV1.first_name
    "Coborrower_Last_Name__c": "Tester",          # CoborrowerV1.last_name
    "Coborrower_Email__c": "terry@example.com",   # CoborrowerV1.email
    "OwnerId": "005G0000007TjGaIAK",
    "RecordTypeId": "0127A0000004LMBQA2",
    "OpportunityContactRoles": {
        "totalSize": 1,
        "done": true,
        "records": [{
            "attributes": {
                "type": "OpportunityContactRole",
                "url": "/services/data/v35.0/sobjects/OpportunityContactRole/00K7A000000Mqg5UAC"
            },
            "OpportunityId": "0067A000002GYjvQAG",
            "Id": "00K7A000000Mqg5UAC",
            "ContactId": "0037A000007dweFQAQ",
            "Contact":{
               "FirstName":"Mark",            # BorrowerV1.first_name
               "LastName":"Tester",           # BorrowerV1.last_name
               "Email":"mark@example.com",    # BorrowerV1.email
               "Birthdate__c": "1950-01-01",  # BorrowerV1.dob
               "Years_In_School__c": 4,       # BorrowerV1.years_in_school
               "Marital_Status__c": "Single", # BorrowerV1.marital_status
               "Citizenship__c": "US Citizen", # BorrowerV1.citizenship
               "Phone": "321-555-1111",       # BorrowerV1.phone
               "Veteran__c": "",              # BorrowerV1.is_veteran
               "MailingAddress":{
                  "city":"San Francisco",   # AddressV1.city
                  "country":"United States",
                  "countryCode":"US",
                  "geocodeAccuracy":null,
                  "latitude":null,
                  "longitude":null,
                  "postalCode":"94111",     # AddressV1.postal_code
                  "state":"California",     # AddressV1.state
                  "stateCode":null,
                  "street":"123 Main Street" # AddressV1.street
               }
            }
        }]
    },
    "Owner": {
        "attributes": {
            "type": "User",
            "url": "/services/data/v35.0/sobjects/User/005G0000007TjGaIAK"
        },
        "Email": "advisor@example.com",
        "Id": "005G0000007TjGaIAK"
    }
}
```
