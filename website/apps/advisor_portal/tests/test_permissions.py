import mock

from django.test import TestCase, override_settings


from advisor_portal.permissions import ModifyOperationsPermission


from loans import factories


class TestModifyOperationsPermission(TestCase):
    @staticmethod
    def generateRequest(path, method):
        return mock.MagicMock(
            _request=mock.MagicMock(
                path=path,
            ),
            method=method,
        )

    def assertPermissionIsGranted(self, request):
        return self.assertTrue(ModifyOperationsPermission().has_permission(request, None))

    def assertPermissionIsNotGranted(self, request):
        return self.assertFalse(ModifyOperationsPermission().has_permission(request, None))

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_non_existing_loan_profile_with_limitation(self):
        request = self.generateRequest(
            '/api/v1/advisor-portal/advisor/loan-profiles-v1/9993313/borrowers/7112/',
            'POST',
        )
        self.assertPermissionIsNotGranted(request)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=False)
    def test_non_existing_loan_profile_without_limitation(self):
        request = self.generateRequest(
            '/api/v1/advisor-portal/advisor/loan-profiles-v1/9993313/borrowers/7112/',
            'POST',
        )
        self.assertPermissionIsGranted(request)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_get_works_for_existing_loan_profile_with_limitation(self):
        lp = factories.LoanProfileV1Factory()
        request = self.generateRequest(
            '/api/v1/advisor-portal/advisor/loan-profiles-v1/{0}/borrowers/7112/'.format(lp.id),
            'GET',
        )
        self.assertPermissionIsGranted(request)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=False)
    def test_get_works_for_existing_loan_profile_without_limitation(self):
        lp = factories.LoanProfileV1Factory()
        request = self.generateRequest(
            '/api/v1/advisor-portal/advisor/loan-profiles-v1/{0}/borrowers/7112/'.format(lp.id),
            'GET',
        )
        self.assertPermissionIsGranted(request)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_restricted_methods_for_existing_non_submitted_loan_profile_with_limitation(self):
        lp = factories.LoanProfileV1Factory()
        url = '/api/v1/advisor-portal/advisor/loan-profiles-v1/{0}/borrowers/7112/'.format(lp.id)
        self.assertPermissionIsGranted(self.generateRequest(url, 'POST'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'PUT'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'PATCH'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'DELETE'))

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=False)
    def test_restricted_methods_for_existing_non_submitted_loan_profile_without_limitation(self):
        lp = factories.LoanProfileV1Factory()
        url = '/api/v1/advisor-portal/advisor/loan-profiles-v1/{0}/borrowers/7112/'.format(lp.id)
        self.assertPermissionIsGranted(self.generateRequest(url, 'POST'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'PUT'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'PATCH'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'DELETE'))

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_restricted_methods_for_existing_submitted_loan_profile_with_limitation(self):
        lp = factories.LoanProfileV1EncompassSyncedFactory()
        url = '/api/v1/advisor-portal/advisor/loan-profiles-v1/{0}/borrowers/7112/'.format(lp.id)
        self.assertPermissionIsNotGranted(self.generateRequest(url, 'POST'))
        self.assertPermissionIsNotGranted(self.generateRequest(url, 'PUT'))
        self.assertPermissionIsNotGranted(self.generateRequest(url, 'PATCH'))
        self.assertPermissionIsNotGranted(self.generateRequest(url, 'DELETE'))

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=False)
    def test_restricted_methods_for_existing_submitted_loan_profile_without_limitation(self):
        lp = factories.LoanProfileV1EncompassSyncedFactory()
        url = '/api/v1/advisor-portal/advisor/loan-profiles-v1/{0}/borrowers/7112/'.format(lp.id)
        self.assertPermissionIsGranted(self.generateRequest(url, 'POST'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'PUT'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'PATCH'))
        self.assertPermissionIsGranted(self.generateRequest(url, 'DELETE'))
