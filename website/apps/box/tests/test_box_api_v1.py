# coding: utf-8
from __future__ import unicode_literals

import logging
import mock

import factory
import boxsdk
import requests

from httmock import with_httmock

from django.test import TestCase

from rest_framework import status

from box import api_v1 as api
from box.utils import box_client_factory
from core.exceptions import ServiceInternalErrorException, ServiceUnavailableException
from core.utils import LogMutingTestMixinBase
from loans.factories import BorrowerV1
from box.factories import (
    box_response_status_code_404,
    box_response_status_code_429,
    box_response_status_code_503,
    box_all_response_status_code_503,
    box_response_timeout
)
from storage.models import Storage


def named_mock(name, **kwargs):
    m = mock.Mock(**kwargs)
    m.name = name
    return m


class BoxApiV1MutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.box.api']
    mute_level = logging.CRITICAL


class BoxApiV1MethodsTest(BoxApiV1MutingMixin, TestCase):
    def setUp(self):
        super(BoxApiV1MethodsTest, self).setUp()
        self.box_client = box_client_factory()

    @mock.patch('boxsdk.client.Client.make_request')
    def test_get_thumbnail_success(self, mocked_make_request):
        fake_content = factory.fuzzy.FuzzyText(length=64).fuzz()
        mocked_make_request.return_value = mock.Mock(content=fake_content)
        result = api.get_thumbnail(mock.Mock())
        self.assertEqual(result, fake_content)

    @mock.patch('boxsdk.client.Client.make_request')
    def test_get_thumbnail_called_client_make_request(self, mocked_make_request):
        api.get_thumbnail(mock.Mock())
        mocked_make_request.assert_called_once()

    @mock.patch('boxsdk.client.Client.make_request')
    def test_get_thumbnail_box_exception(self, mocked_make_request):
        mocked_make_request.side_effect = boxsdk.exception.BoxAPIException('status')
        self.assertIsNone(api.get_thumbnail(mock.Mock()))

    @mock.patch('boxsdk.client.Client.make_request')
    def test_get_thumbnail_requests_exception(self, mocked_make_request):
        mocked_make_request.side_effect = requests.exceptions.RequestException('status')
        self.assertIsNone(api.get_thumbnail(mock.Mock()))


class BoxExceptionHandler(BoxApiV1MutingMixin, TestCase):

    def setUp(self):
        super(BoxExceptionHandler, self).setUp()
        self.box_client = box_client_factory()
        self.box_folder = self.box_client.file(11111)

    @with_httmock(box_response_status_code_503)
    def test_box_response_status_code_503(self):
        self.assertEqual(box_response_status_code_503.call, {'count': 0, 'called': False})
        with self.assertRaises(ServiceUnavailableException):
            api.box_file_rename(self.box_folder, 'new_mock_name')
        self.assertEqual(box_response_status_code_503.call, {'count': 2, 'called': True})

    @with_httmock(box_response_status_code_429)
    def test_box_response_status_code_429(self):
        self.assertEqual(box_response_status_code_429.call, {'count': 0, 'called': False})
        with self.assertRaises(ServiceUnavailableException):
            api.box_file_rename(self.box_folder, 'new_mock_name')
        self.assertEqual(box_response_status_code_429.call, {'count': 2, 'called': True})

    @with_httmock(box_response_status_code_404)
    def test_box_response_status_code_404(self):
        self.assertEqual(box_response_status_code_404.call, {'count': 0, 'called': False})
        with self.assertRaises(ServiceInternalErrorException):
            api.box_file_rename(self.box_folder, 'new_mock_name')
        self.assertEqual(box_response_status_code_404.call, {'count': 1, 'called': True})

    @with_httmock(box_response_timeout)
    def test_requests_exception(self):
        self.assertEqual(box_response_timeout.call, {'count': 0, 'called': False})
        with self.assertRaises(ServiceUnavailableException):
            api.box_file_rename(self.box_folder, 'new_mock_name')
        self.assertEqual(box_response_timeout.call, {'count': 1, 'called': True})


class SubfolderGetTest(BoxApiV1MutingMixin, TestCase):
    def setUp(self):
        self.parent = mock.Mock(
            object_id='PARENT-ID',
            get_items=lambda x: (named_mock('aaa'), named_mock('bbb'), named_mock('ccc'))
        )
        super(SubfolderGetTest, self).setUp()

    def test_found(self):
        name = 'bbb'
        subfolder = api.box_subfolder_get(self.parent, name)
        self.assertIsNotNone(subfolder)
        self.assertEqual(subfolder.name, name)

    def test_not_found(self):
        name = 'eee'
        folder = api.box_subfolder_get(self.parent, name)
        self.assertIsNone(folder)

    def test_not_found_should_exist(self):
        name = 'eee'
        folder = api.box_subfolder_get(self.parent, name, should_exist=True)
        self.assertIsNone(folder)


class FolderUpdateTest(BoxApiV1MutingMixin, TestCase):
    def setUp(self):
        self.parent = mock.Mock(
            object_id='PARENT-ID',
            get_items=lambda x: (named_mock('aaa'), named_mock('bbb'), named_mock('ccc'))
        )
        self.exists_exc = boxsdk.exception.BoxAPIException(
            status=412, code='item_name_in_use')
        super(FolderUpdateTest, self).setUp()

    def test_successful_create_with_description(self):
        name = 'eee'
        description = 'a description'
        self.parent.create_subfolder = named_mock
        folder = api.box_folder_save(self.parent, name, [], description=description)
        self.assertIsNotNone(folder)
        self.assertEqual(name, folder.name)
        args, kwargs = folder.update_info.call_args
        self.assertFalse(args)
        self.assertEqual({'data': {'description': description}}, kwargs)

    def test_successful_create_no_acls(self):
        name = 'eee'
        self.parent.create_subfolder = named_mock
        folder = api.box_folder_save(self.parent, name, [])
        self.assertIsNotNone(folder)
        self.assertEqual(name, folder.name)

    def test_successful_may_exist_no_acls(self):
        def create_subfolder(name):
            raise self.exists_exc
        self.parent.create_subfolder = create_subfolder
        name = 'bbb'
        folder = api.box_folder_save(self.parent, name, [], may_exist=True)
        self.assertIsNotNone(folder)
        self.assertEqual(name, folder.name)

    def test_may_exist_no_acls_error_raises_exception(self):
        def create_subfolder(name):
            raise boxsdk.exception.BoxAPIException(status=400, code='fake_error')
        self.parent.create_subfolder = create_subfolder
        name = 'bbb'
        with self.assertRaises(ServiceInternalErrorException) as cm:
            api.box_folder_save(self.parent, name, [], may_exist=True)

        # Check ServiceInternalErrorException status_code
        self.assertEqual(cm.exception.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check parent exception BoxAPIException data
        self.assertEqual(cm.exception.parent_exc.status, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.parent_exc.code, 'fake_error')

    def test_may_not_exist_no_acls_raises_exists_exception(self):
        def create_subfolder(name):
            raise self.exists_exc
        self.parent.create_subfolder = create_subfolder
        name = 'bbb'
        with self.assertRaises(ServiceInternalErrorException) as cm:
            api.box_folder_save(self.parent, name, [], may_exist=False)

        # Check ServiceInternalErrorException status_code
        self.assertEqual(cm.exception.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check parent exception BoxAPIException data
        self.assertEqual(cm.exception.parent_exc.status, self.exists_exc.status)
        self.assertEqual(cm.exception.parent_exc.code, self.exists_exc.code)


# pylint: disable=W0212
class BorrowerFolderNameTest(BoxApiV1MutingMixin, TestCase):
    def test_both_names_present(self):
        first = 'Firstly'
        last = 'Lastly'
        uniquifier = 'PI314'
        borrower = BorrowerV1(first_name=first, last_name=last)
        folder_name = api._borrower_folder_name_get(borrower, uniquifier)
        self.assertEqual('Lastly, Firstly PI314', folder_name)

    def test_first_name_present(self):
        first = 'Firstly'
        last = ''
        uniquifier = 'PI314'
        borrower = BorrowerV1(first_name=first, last_name=last)
        folder_name = api._borrower_folder_name_get(borrower, uniquifier)
        self.assertEqual('Firstly PI314', folder_name)

    def test_last_name_present(self):
        first = ''
        last = 'Lastly'
        uniquifier = 'PI314'
        borrower = BorrowerV1(first_name=first, last_name=last)
        folder_name = api._borrower_folder_name_get(borrower, uniquifier)
        self.assertEqual('Lastly, PI314', folder_name)

    def test_no_name_present(self):
        first = ''
        last = ''
        uniquifier = 'PI314'
        borrower = BorrowerV1(first_name=first, last_name=last)
        folder_name = api._borrower_folder_name_get(borrower, uniquifier)
        self.assertEqual('PI314', folder_name)


class FolderAclsSetTest(BoxApiV1MutingMixin, TestCase):
    """ Class to test Folder ACL was set properly """
    def test_success(self):
        """ Happy path with new emails """
        mock_folder = mock.Mock(add_collaborator=mock.Mock(return_value=None))
        acls = [('t-1@example.com', api.ADVISOR_ACL),
                ('t-2@example.org', api.SPECIALIST_ACL)]
        api.box_folder_acls_set(mock_folder, acls)
        self.assertTrue(mock_folder.add_collaborator.called)
        call_args_list_exp = [(('t-1@example.com', api.ADVISOR_ACL, False),),
                              (('t-2@example.org', api.SPECIALIST_ACL, False),)]
        self.assertEqual(call_args_list_exp,
                         mock_folder.add_collaborator.call_args_list)

    def test_success_already_exists(self):
        """ Happy path of adding someone who already has access """
        exc = boxsdk.exception.BoxAPIException(status='402', code='user_already_collaborator')
        mock_folder = mock.Mock(add_collaborator=mock.Mock(side_effect=exc))
        acls = [('t-1@example.com', api.ADVISOR_ACL),
                ('t-2@example.org', api.SPECIALIST_ACL)]
        api.box_folder_acls_set(mock_folder, acls)
        self.assertTrue(mock_folder.add_collaborator.called)
        call_args_list_exp = [(('t-1@example.com', api.ADVISOR_ACL, False),),
                              (('t-2@example.org', api.SPECIALIST_ACL, False),)]
        self.assertEqual(call_args_list_exp,
                         mock_folder.add_collaborator.call_args_list)

    def test_stops_at_first_failure(self):
        """ Stop adding people after the first failure """
        exc = boxsdk.exception.BoxAPIException(status='402', code='bad_code')
        mock_folder = mock.Mock(add_collaborator=mock.Mock(side_effect=exc))
        acls = [('t-1@example.com', api.ADVISOR_ACL),
                ('t-2@example.org', api.SPECIALIST_ACL)]
        with self.assertRaises(ServiceInternalErrorException):
            api.box_folder_acls_set(mock_folder, acls)
        self.assertTrue(mock_folder.add_collaborator.called)
        call_args_list_exp = [(('t-1@example.com', api.ADVISOR_ACL, False),)]
        self.assertEqual(call_args_list_exp,
                         mock_folder.add_collaborator.call_args_list)

    def test_notifies_internal_user(self):
        """ Tests that we notify internal users """
        mock_folder = mock.Mock(add_collaborator=mock.Mock(return_value=None))
        acls = [('t-1@sample.com', api.ADVISOR_ACL)]
        api.box_folder_acls_set(mock_folder, acls)
        mock_folder.add_collaborator.assert_called_with('t-1@sample.com', api.ADVISOR_ACL, True)

    def test_does_not_notify_external_user(self):
        """ Tests that we do not notify external users """
        mock_folder = mock.Mock(add_collaborator=mock.Mock(return_value=None))
        acls = [('t-1@example.com', api.ADVISOR_ACL)]
        api.box_folder_acls_set(mock_folder, acls)
        mock_folder.add_collaborator.assert_called_with('t-1@example.com', api.ADVISOR_ACL, False)


class LoanProfileStorageUpdateTest(BoxApiV1MutingMixin, TestCase):
    def setUp(self):
        ma_storage_id = '987654321'
        loan_profile = mock.Mock(
            advisor=mock.Mock(),
            id=12345678,
            is_active=True,
            storage_id=None,
            uniquifier='AABB')
        loan_profile.advisor.storages.filter().first.return_value = mock.Mock(
            storage_id=ma_storage_id)
        loan_profile.borrowers.first = mock.Mock(
            return_value=BorrowerV1(first_name='Firstly', last_name='Lastly'))
        self.ma_storage_id = ma_storage_id
        self.loan_profile = loan_profile
        self.external_template = mock.Mock(storage_id='1a2b3cd4e5f6g7h8')
        super(LoanProfileStorageUpdateTest, self).setUp()

    def test_no_borrower_fail(self):
        self.loan_profile.borrowers.first = mock.Mock(side_effect=[None])
        rc = api.get_or_create_loan_profile_box_folder(self.loan_profile, self.external_template)
        self.assertIsNone(rc)

    def test_borrower_blank_name_fail(self):
        self.loan_profile.borrowers.first = mock.Mock(
            return_value=BorrowerV1(first_name='   ', last_name='   '))
        rc = api.get_or_create_loan_profile_box_folder(self.loan_profile, self.external_template)
        self.assertIsNone(rc)

    def test_no_advisor_fail(self):
        self.loan_profile.advisor = None
        rc = api.get_or_create_loan_profile_box_folder(self.loan_profile, self.external_template)
        self.assertIsNone(rc)

    def test_no_advisor_storage_fail(self):
        self.loan_profile.advisor.storages.filter.return_value.first.return_value = None
        rc = api.get_or_create_loan_profile_box_folder(self.loan_profile, self.external_template)
        self.assertIsNone(rc)

    @mock.patch('box.api_v1.box_subfolder_get')
    @mock.patch('box.api_v1.box_client_factory')
    def test_subfolder_exists_success(self,
                                      mocked_factory,
                                      mocked_subfolder_get):
        self.assertIs(mocked_factory, api.box_client_factory)
        mocked_subfolder_get.return_value = mock.Mock(id='123451234')
        rc = api.get_or_create_loan_profile_box_folder(self.loan_profile, self.external_template)
        self.assertIsNotNone(rc)
        self.assertEqual('123451234', rc)

    @mock.patch('box.api_v1.customer_loan_internal_folders_create')
    @mock.patch('box.api_v1.customer_loan_external_folders_create')
    @mock.patch('box.api_v1.box_folder_save')
    @mock.patch('box.api_v1.box_subfolder_get')
    @mock.patch('box.api_v1.box_client_factory')
    def test_subfolder_create_success(self,
                                      mocked_factory,
                                      mocked_subfolder_get,
                                      mocked_update,
                                      mocked_external_create,
                                      mocked_internal_create):
        self.assertIs(mocked_factory, api.box_client_factory)
        mocked_subfolder_get.return_value = None
        mocked_update.return_value = mock.Mock(id='21212121')
        rc = api.get_or_create_loan_profile_box_folder(self.loan_profile, self.external_template)
        self.assertEqual('21212121', rc)
        self.assertTrue(mocked_update.called)
        self.assertTrue(mocked_external_create.called)
        self.assertTrue(mocked_internal_create.called)


class InternalFoldersCreateTestCase(BoxApiV1MutingMixin, TestCase):
    @mock.patch('box.api_v1.box_folder_save')
    def test_call_count(self, box_folder_save):
        test_box_folder_mock = mock.MagicMock()
        box_folder_data = {
            'name': 'Submission',
            'object_id': '777',
            'parent': {'id': '123'}
        }
        test_box_folder_mock.configure_mock(**box_folder_data)

        box_folder_save.return_value = test_box_folder_mock
        base = 'Lastly, Firstly UNIQ'
        parent_folder = mock.Mock()
        api.customer_loan_internal_folders_create(base, parent_folder)
        subfolder_count = len(api.CUSTOMER_INTERNAL_SUBFOLDERS_FORMATS)
        self.assertEqual(subfolder_count, len(box_folder_save.call_args_list))

        # Ensure Submission storage is created
        storages = Storage.objects.filter(role=api.SUBMISSION)
        self.assertEqual(storages.count(), 1)
        submission_storage = storages.first()
        self.assertEqual(submission_storage.name, box_folder_data['name'])
        self.assertEqual(submission_storage.storage_id, box_folder_data['object_id'])
        self.assertEqual(submission_storage.box_parent_folder_id, box_folder_data['parent']['id'])


class TestServiceUnavailableHandler(BoxApiV1MutingMixin, TestCase):
    def setUp(self):
        super(TestServiceUnavailableHandler, self).setUp()
        self.service_name = 'Box'
        self.exception_msg = str(ServiceUnavailableException())
        self.loan_profile = mock.Mock(
            advisor=mock.Mock(),
            id=12345678,
            guid='123',
            is_active=True,
            storage_id=None,
            storage=mock.Mock(storage_id='123'),
            uniquifier='AABB')
        self.loan_profile.advisor.storages.filter().first.return_value = mock.Mock(
            storage_id='987654321')
        self.loan_profile.borrowers.first = mock.Mock(
            return_value=BorrowerV1(first_name='Firstly', last_name='Lastly'))
        self.borrower = mock.Mock(
            loan_profile=self.loan_profile
        )
        self.document_obj = mock.Mock(
            id=123,
            storage=mock.Mock(storage_id='123'),
            document_id='123',
            save=mock.Mock()
        )

    def _check_called_function_args(self, called_function):
        call_args = called_function.call_args[0]
        self.assertEqual(call_args[0], self.loan_profile.guid)
        self.assertEqual(call_args[1], self.service_name)
        self.assertEqual(call_args[2], self.exception_msg)

    @with_httmock(box_all_response_status_code_503)
    @mock.patch('core.utils.send_exception_notification')
    def test_get_or_create_loan_profile_box_folder_service_unavailable(self, mocked_send_exception_notification):
        external_template = mock.Mock(storage_id='1a2b3cd4e5f6g7h8')
        with self.assertRaises(ServiceUnavailableException):
            api.get_or_create_loan_profile_box_folder(self.loan_profile, external_template)
        self._check_called_function_args(mocked_send_exception_notification)

    @with_httmock(box_all_response_status_code_503)
    @mock.patch('core.utils.send_exception_notification')
    def test_loan_profile_folder_add_advisor_service_unavailable(self, mocked_send_exception_notification):
        with self.assertRaises(ServiceUnavailableException):
            api.loan_profile_folder_add_advisor(self.loan_profile, mock.Mock())
        self._check_called_function_args(mocked_send_exception_notification)

    @with_httmock(box_all_response_status_code_503)
    @mock.patch('core.utils.send_exception_notification')
    def test_store_credit_report_service_unavailable(self, mocked_send_exception_notification):
        with self.assertRaises(ServiceUnavailableException):
            api.store_credit_report(self.loan_profile, mock.Mock())
        self._check_called_function_args(mocked_send_exception_notification)

    @with_httmock(box_all_response_status_code_503)
    @mock.patch('core.utils.send_exception_notification')
    def test_store_consumer_pdf_service_unavailable(self, mocked_send_exception_notification):
        with self.assertRaises(ServiceUnavailableException):
            api.store_consumer_pdf(self.loan_profile, mock.Mock())
        self._check_called_function_args(mocked_send_exception_notification)

    @with_httmock(box_all_response_status_code_503)
    @mock.patch('core.utils.send_exception_notification')
    def test_store_aus_service_unavailable(self, mocked_send_exception_notification):
        with self.assertRaises(ServiceUnavailableException):
            api.store_aus(mock.Mock(), self.loan_profile, mock.Mock())
        self._check_called_function_args(mocked_send_exception_notification)
