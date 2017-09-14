from django.core.urlresolvers import reverse

from accounts import factories as accounts_factories
from accounts.tests.helpers import JWTAuthAPITestCase
from contacts.factories import LocationFactory


class TestLocationZipcodeLookup(JWTAuthAPITestCase):
    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()

    def _get_zipcode(self, zipcode):
        return self.client.get(
            reverse('advisor-portal:zipcode_lookup', args=[zipcode]),
            HTTP_AUTHORIZATION=self.get_jwt_auth()
        )

    def test_get_by_non_existent_zipcode_returns_404(self):
        response = self._get_zipcode(11111111)
        self.assertEqual(response.status_code, 404)

    def test_get_by_existing_zipcode(self):
        LocationFactory(zipcode=10001, state='NY', county='New York', city='New York')
        response = self._get_zipcode(10001)
        self.assertEqual(response.status_code, 200)


class TestLocationLookupView(JWTAuthAPITestCase):
    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()

    def _get_data(self, city=None, state=None):
        if not city or not state:
            url = reverse('advisor-portal:location_lookup')
        else:
            url = '{0}?city={1}&state={2}'.format(
                reverse('advisor-portal:location_lookup'),
                city, state,
            )
        return self.client.get(
            url,
            HTTP_AUTHORIZATION=self.get_jwt_auth()
        )

    def test_get_without_parameters_returns_400(self):
        response = self._get_data()
        self.assertEqual(response.status_code, 400)

    def test_get_non_existent_data_returns_404(self):
        response = self._get_data(city='Blah Blah Village', state='CA')
        self.assertEqual(response.status_code, 404)

    def test_get_existing_data(self):
        LocationFactory(zipcode=99998, state='CA', county='San Francisco', city='San Francisco')
        LocationFactory(zipcode=99999, state='CA', county='San Francisco', city='San Francisco')
        response = self._get_data(city='San Francisco', state='CA')
        self.assertEqual(response.status_code, 200)

    def test_get_city_with_hyphen_and_in_lower_case_returns_data(self):
        LocationFactory(zipcode=99998, state='CA', county='San Francisco', city='San Francisco')
        LocationFactory(zipcode=99999, state='CA', county='San Francisco', city='San Francisco')
        response = self._get_data(city='san-francisco', state='CA')
        self.assertEqual(response.status_code, 200)
