# website/apps/mortgage_profiles

This is a high level overview of how the mortgage_profiles app works. See code documentation for more detail. 
Fee and calculations information in mortech/README.md .

_Summary_
* Retrieves data for the rate quote form to form request. 
* Manages api requests and responses to mortech.
* Saves lender data from api response.

Company Documentation: https://sample.box.com/mortech-tech-docs
Diagram Overview: `documentation/Mortech/rate-quote-service-diagram.pdf`

## Local Setup
* Go to sample/support/mortech_test
* Run `./runtestserver.sh`

This allows testing responses without sending requests to the mortech api.
Request access to credentials and add them to settings/dev.py. 

## Rate Quote Form
* SITE PATH: /rate-quote
* APP VIEW: views.py
* TEMPLATES: /assets-rc/src/templates/rate_quote
* JAVASCRIPT: /assets-rc/src/js/angular/rate_quote

## API Requests
`MortgageProfile` (models/mortgage_profiles.py): the model for the form data. All data submitted in the form generates an instance of this model. The instance data is mapped to each request parameter. Parameters can be viewed in the Mortech API Documentation.

`MortechCalculations` (mortech/calculations.py): the class where the request values are mapped and/or calculated based on the `MortgageProfile` form data.

`MortechApi` (mortech/api.py): the class for taking those parameters and values, and building the request. It then sends it to the rate quote service.

## API Response
`MortechApi` receives the response and parses the xml document into a dictionary. This allows the app to pull lender data and store it. It is this data that is used to return results to the user. 

`MortechRequest` (models/lenders.py): tracks each request made for a mortgage profile.

`MortechLender` (models/lenders.py): saves basic data about loan products. Queries are then made against it instead of generating a new request for new data. 

`MortechDirector` (mortech/results.py): sends query results back to the view. For example, if the user requested to see 3 yr ARM products, it would query that product from the lenders.
