# Fee Calculations

These fees should be run by decision-makers and verified to be the correct implementation for the rate quote
form.

### Fees returned in the rate quote results
Fee names can vary from lender to lender. Ben.Robinson@sample.com is the point of contact to receive updates on fee names.

- Underwriting (aka: Admin,  Admin Fee, Administration, Administration Fee, Commitment, FMC Origination Fee
    Funding Fee, Lender Fee, Lender Fees, Underwriting, UW Fee)
- Prepaid Interest
- Tax Service Fee
- Cost of chosen rate (loan discount points)
- Escrowed insurance (Homeowner's Insurance)
- Escrowed taxes (Taxes)
- Mortgage Insurance Premium
- Funding Fee (default, added to disclaimer)

### Calculations
_Prepaid Interest_
`loan amount * rate / term`

_Tax Service Fee_
`Defaults to 69`

_Cost of chosen rate_
`loan amount * points / 100`

_Escrowed Insurance_
`loan amount * 0.00375 / 12`

_Escrowed Taxes_
`property value * 0.0125 / 12`

_Total Fees_
`chosen rate + underwriting + tax service + upfront + prepaid interest`

_Total Monthly Payment_
`monthly payment + escrowed ins + escrowed taxes + mortgage insurance`


