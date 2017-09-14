from rest_framework.test import APITestCase

from rest_framework_jwt import utils


class JWTAuthAPITestCase(APITestCase):
    def get_jwt_auth(self):
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)

        return 'JWT {0}'.format(token)
