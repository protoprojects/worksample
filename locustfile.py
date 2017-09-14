import json
from functools import partial

from locust import HttpLocust, TaskSet, task

HTTP_BASIC_AUTH_CREDENTIALS = ('pamela', 'cocacola',)


def patched_request(urlpath):
    """
    Inject updated get and post functions
    Updates:
    - csrf token
    - request type to ajax
    - content type to json
    """
    def inner(f):
        def wrapped(self, *args, **kwargs):
            cookies = self.client.get(urlpath, verify=False, auth=HTTP_BASIC_AUTH_CREDENTIALS).cookies
            token = cookies.get('csrftoken')
            headers = {
                'X-CSRFToken': token,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
            f_kwargs = dict(verify=False, auth=HTTP_BASIC_AUTH_CREDENTIALS, headers=headers, cookies=cookies)
            get = partial(self.client.get, **f_kwargs)
            post = partial(self.client.post, **f_kwargs)
            put = partial(self.client.put, **f_kwargs)
            args += (get, post, put)
            return f(self, *args, **kwargs)
        return wrapped
    return inner


class BasicUserBehavior(TaskSet):
    @task(1)
    @patched_request('/')
    def make_consultation_request(self, get, post, put):
        """
        Main action at homepage
        """
        data = {
            "preferredTime": "anytime",
            "mortgageProfileKind": "purchase",
            "mortgageTiming": "immediate",
            "firstName": "a",
            "lastName": "a",
            "phone": "(111) 111-1111",
            "email": "a@a.com"
        }
        post('/api/v1/contact-requests/consultation/', json.dumps(data))

    @task
    @patched_request('/rate-quote/#/property-location')
    def purchase_rate_quote_steps(self, get, post, put):
        get('/api/v1/contact-requests/location/', params={'state': 'CA'})

        # choose loan purpose
        post('/api/v1/mortgage-profiles/purchase/', json.dumps({
            "propertyState": "California",
            "propertyCounty": "Alameda County",
            "kind": "purchase"}))

        response = get('/api/v1/mortgage-profiles/active/')
        active_profile_id = response.json().get('id')
        if not active_profile_id:
            return

        api_url = '/api/v1/mortgage-profiles/purchase/%s/' % active_profile_id

        # choose purchase timing
        put(api_url, json.dumps({
            "kind": "purchase",
            "targetValue": None,
            "propertyCounty": "Alameda County",
            "creditRating": "",
            "purchaseType": "",
            "purchaseDownPayment": None,
            "propertyState": "California",
            "ownershipTime": "",
            "propertyZipcode": "",
            "purchaseTiming": "researching_options",
            "isVeteran": None,
            "id": active_profile_id}))

        # choose purcase type
        put(api_url, json.dumps({
            "kind": "purchase",
            "targetValue": None,
            "propertyCounty": "Alameda County",
            "creditRating": "",
            "purchaseType": "first_time_homebuyer",
            "purchaseDownPayment": None,
            "propertyState": "California",
            "ownershipTime": "",
            "propertyZipcode": "",
            "purchaseTiming": "researching_options",
            "isVeteran": False,
            "id": active_profile_id}))

        # choose purchase property value
        put(api_url, json.dumps({
            "kind": "purchase",
            "targetValue": "1000000",
            "propertyCounty": "Alameda County",
            "creditRating": "",
            "purchaseType": "first_time_homebuyer",
            "purchaseDownPayment": 200000,
            "propertyState": "California",
            "ownershipTime": "",
            "propertyZipcode": "",
            "purchaseTiming": "researching_options",
            "isVeteran": False,
            "id": active_profile_id}))

        # choose ownership
        put(api_url, json.dumps({
            "kind": "purchase",
            "targetValue": 1000000,
            "propertyCounty": "Alameda County",
            "creditRating": "",
            "purchaseType": "first_time_homebuyer",
            "purchaseDownPayment": 200000,
            "propertyState": "California",
            "ownershipTime": "long_term",
            "propertyZipcode": "",
            "purchaseTiming": "researching_options",
            "isVeteran": False,
            "id": active_profile_id}))

        # choose credit rating
        put(api_url, json.dumps({
            "kind": "purchase",
            "targetValue": 1000000,
            "propertyCounty": "Alameda County",
            "creditRating": "740_759",
            "purchaseType": "first_time_homebuyer",
            "purchaseDownPayment": 200000,
            "propertyState": "California",
            "ownershipTime": "long_term",
            "propertyZipcode": "",
            "purchaseTiming": "researching_options",
            "isVeteran": False,
            "id": active_profile_id}))

        # final page
        get('/api/v1/mortgage-profiles/loan-sifter/')


class WebsiteUser(HttpLocust):
    task_set = BasicUserBehavior
    min_wait = 5000
    max_wait = 9000
