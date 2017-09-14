# Advisor Portal API Reference

Here is the list of available endpoints.
Description is provided when endpoint definition is not obvious.


## LOAN PROFILE

`/loan-profiles-v1/`<sup>[POST]</sup>

`/loan-profiles-v1/?is_submitted=[True,False]` <sup>[GET]</sup>  
(`is_submitted` filter means that LoanProfile is submitted to Encompass)

`/loan-profiles-v1/:id/` <sup>[GET, PATCH]</sup>

`/loan-profiles-v1/:id/new_property_address/` <sup>[GET, POST, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/confirm_demographics_questions/` <sup>[POST]</sup>  
Confirm demographics questions for a loan profile, there are no ability
to revert this.

`/loan-profiles-v1/:id/storage/` <sup>[POST]</sup>  
Create a storage for loan profile.

`/loan-profiles-v1/:id/los_guid/` <sup>[POST]</sup>  
Submit loan profile to encompass.

`/loan-profiles-v1-sync-in-progress/`<sup>[GET]</sup>  
Retrieve a list of loan profiles which are currently syncing with Encompass.

## BORROWER

`/loan-profiles-v1/:id/borrowers/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/mailing_address/` <sup>[GET, POST, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/demographics/` <sup>[GET, POST, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/realtor/` <sup>[GET, POST, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/previous-addresses/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/previous-addresses/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/previous-employments/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/previous-employments/:id/` <sup>[GET, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/previous-employments/:id/address/` <sup>[GET, POST, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/previous-employments/:id/company_address/` <sup>[GET, POST, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/holding-assets/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/holding-assets/:id/` <sup>[GET, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/holding-assets/:id/institution_address/` <sup>[GET, POST, PATCH, DELETE]</sup> 

To transfer ownership from borrower to coborrower, or assign in both to borrower and coborrower,   
need to `PUT` with `{"borrowerId":1, "coborrowerId":1}`  
**Please note**, `PUT` replaces content of object, so if you will send only `borrowerId` or only  
`coborrowerId`, it will be assigned only to it, all previous relationships will be removed.

---

`/loan-profiles-v1/:id/borrowers/:id/vehicle-assets/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/vehicle-assets/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/insurance-assets/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/insurance-assets/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/incomes/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/incomes/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/expenses/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/expenses/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/liabilities/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/liabilities/:id/` <sup>[GET, PATCH, DELETE]</sup>


## COBORROWER

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/` <sup>[GET, POST, PATCH, DELETE]</sup>
<sup>Restriction on `POST` - will not have ability to create more that one coborrowers</sup>


`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/mailing_address/` <sup>[GET, POST, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/demographics/` <sup>[GET, POST, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/realtor/` <sup>[GET, POST, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/realtor/address/` <sup>[GET, POST, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/previous-addresses/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/previous-addresses/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/previous-employments/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/previous-employments/:id/` <sup>[GET, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/previous-employments/:id/address/` <sup>[GET, POST, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/previous-employments/:id/company_address/` <sup>[GET, POST, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/holding-assets/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/holding-assets/:id/` <sup>[GET, PATCH, DELETE]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/holding-assets/:id/institution_address/` <sup>[GET, POST, PATCH, DELETE]</sup>  

To transfer ownership from borrower to coborrower, or assign in both to borrower and coborrower,   
need to `PUT` with `{"borrowerId":1, "coborrowerId":1}`  
**Please note**, `PUT` replaces content of object, so if you will send only `borrowerId` or only  
`coborrowerId`, it will be assigned only to it, all previous relationships will be removed.

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/vehicle-assets/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/vehicle-assets/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/insurance-assets/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/insurance-assets/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/incomes/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/incomes/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/expenses/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/expenses/:id/` <sup>[GET, PATCH, DELETE]</sup>

---

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/liabilities/` <sup>[GET, POST]</sup>

`/loan-profiles-v1/:id/borrowers/:id/coborrowers/:id/liabilities/:id/` <sup>[GET, PATCH, DELETE]</sup>
