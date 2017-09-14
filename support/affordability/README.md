API contract
============

## Request

**New inputs:**

* monthlyDebt(integer)
* monthlyIncome(integer)

**Rate Quote inputs (MortgageProfile):**

* kind (string)
* propertyState (string)
* purchaseDownPayment (string)
* propertyOccupation (string)
* propertyType (string)
* ownershipTime (string)
* creditScore (string)
* propertyZipcode (string) 
* propertyCity (string)
* propertyCounty (string)

City, zipcode and county are only required for the generation of MortgageProfile.

**Example:**
```json
{
    "kind": "purchase",
    "monthlyDebt": 1000,
    "monthlyIncome": 5000,
    "propertyState": "California",
    "credit_score": 760,
    "propertyOccupation": "primary",
    "ownership_time": "long_term",
    "property_type": "single_family",
    "propertyCity": "San Francisco",
    "propertyZipcode": "94111",
    "propertyCounty": "San Francisco"
}
```
## Response

**All outputs:**

* id (integer, request id)
* apr (string)
* rate (string)
* ltv (string)
* scenarios (list)

_Data contained in scenarios list:_
* Scenario (object)

_Data contained in a Scenario:_
* id (integer, scenario id)
* monthly_payments (decimal)
* down_payment (decimal)
* property_value (decimal)
* loan_amount (decimal)
* ratio_used (string)
* ratio (decimal)
* ratio_percent (integer)


**Example**
```json
{
    "id": 1,
    "apr": "1.750",
    "rate": "3.000",
    "ltv": ".50",
    "scenarios": [
        {
            "id": 23,
            "monthly_payments": "1200.00",
            "down_payment": "10000.00",
            "property_value": "550000.00",
            "loan_amount": "540000.00",
            "ratio_used": "dti",
            "ratio": 1.000,
            "ratio_percent": 100
        },
        {
            "id": 24,
            "monthly_payments": "1400.00",
            "down_payment": "15000.00",
            "property_value": "550000.00",
            "loan_amount": "535000.00",
            "ratio_used": "dti",
            "ratio": 1.000,
            "ratio_percent": 100
        },
        {
            "id": 25,
            "monthly_payments": "1600.00",
            "down_payment": "20000.00",
            "property_value": "550000.00",
            "loan_amount": "530000.00",
            "ratio_used": "dti",
            "ratio": 1.000,
            "ratio_percent": 100
        }
    ]
}
```
