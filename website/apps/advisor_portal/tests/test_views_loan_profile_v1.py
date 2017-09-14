# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import importlib
import logging
import threading
import unittest
import mock

from django.db.utils import DEFAULT_DB_ALIAS, ConnectionHandler
from django.conf import settings
from django.core.urlresolvers import resolve, reverse
from django.test import override_settings, TransactionTestCase

from rest_framework import status

from core.utils import db_connection_close
from accounts import factories as accounts_factories
from loans import factories as loan_factories
from loans.models import (
    AddressV1, BorrowerV1, CoborrowerV1, ContactV1,
    DemographicsV1, EmploymentV1, HoldingAssetV1,
    InsuranceAssetV1, LoanProfileV1, VehicleAssetV1,
    IncomeV1, ExpenseV1, LiabilityV1,
)
from storage import factories as storage_factories

from advisor_portal.tests.helpers import (
    AdvisorCRUDTestMixin, AdvisorAPITestCase
)

##########
# MIXINS #
##########


class BorrowerResourceViewTestMixin(AdvisorCRUDTestMixin):
    url_list = None
    url_detail = None
    tested_model = None
    tested_model_rel_name = None

    is_coborrower = False

    def _get_view(self):
        args = ([self.borrower.borrower.loan_profile.id, self.borrower.borrower.id, self.borrower.id]
                if self.is_coborrower
                else [self.borrower.loan_profile.id, self.borrower.id])
        view_func = resolve(reverse(self.url_list, args=args)).func
        view_module = importlib.import_module(view_func.__module__)
        view = getattr(view_module, view_func.__name__)
        return view

    def _create(self, data=None, with_auth=True):
        if self.is_coborrower:
            args = [self.borrower.borrower.loan_profile.id, self.borrower.borrower.id, self.borrower.id, ]
        else:
            args = [self.borrower.loan_profile.id, self.borrower.id, ]

        if not data and hasattr(self, '_get_creation_data'):
            data = self._get_creation_data()
        return self.client.post(
            reverse(self.url_list, args=args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _retrieve(self, obj_id, with_auth=True):
        if self.is_coborrower:
            args = [
                self.borrower.borrower.loan_profile.id,
                self.borrower.borrower.id,
                self.borrower.id,
                obj_id
            ]
        else:
            args = [self.borrower.loan_profile.id, self.borrower.id, obj_id, ]

        return self.client.get(
            reverse(self.url_detail, args=args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _update(self, obj_id, data=None, with_auth=True):
        if self.is_coborrower:
            args = [
                self.borrower.borrower.loan_profile.id,
                self.borrower.borrower.id,
                self.borrower.id,
                obj_id
            ]
        else:
            args = [self.borrower.loan_profile.id, self.borrower.id, obj_id, ]

        return self.client.patch(
            reverse(self.url_detail, args=args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _delete(self, obj_id, with_auth=True):
        if self.is_coborrower:
            args = [
                self.borrower.borrower.loan_profile.id,
                self.borrower.borrower.id,
                self.borrower.id,
                obj_id
            ]
        else:
            args = [self.borrower.loan_profile.id, self.borrower.id, obj_id, ]

        return self.client.delete(
            reverse(self.url_detail, args=args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _create_obj_of_another_advisor(self):
        raise NotImplementedError()

    def _create_obj(self, *args, **kwargs):
        raise NotImplementedError()

    def _get_data_after_update(self):
        raise NotImplementedError()

    def test_successful_create(self):
        self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(), 0)
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(), 1)

    def test_creation_without_auth_returns_401(self):
        response = self._create(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_retrieve(self):
        obj_id = self._create_obj()
        response = self._retrieve(obj_id=obj_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_in_case_of_inactive_borrower_returns_404(self):
        try:
            self.borrower.is_active = False
            self.borrower.save()
            obj_id = self._create_obj()
            response = self._retrieve(obj_id=obj_id)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        finally:
            self.borrower.is_active = True
            self.borrower.save()

    def test_retrieve_obj_of_another_advisor_returns_404(self):
        obj_id = self._create_obj_of_another_advisor()
        response = self._retrieve(obj_id=obj_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_without_auth_returns_401(self):
        obj_id = self._create_obj()
        response = self._retrieve(obj_id=obj_id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_update(self):
        obj_id = self._create_obj()
        data = self._get_data_after_update()
        response = self._update(obj_id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        obj = self.tested_model.objects.get(id=obj_id)
        for key in data.keys():
            self.assertEqual(getattr(obj, key), data[key])

    def test_update_without_auth_returns_401(self):
        obj_id = self._create_obj()
        response = self._update(obj_id, data=self._get_data_after_update(), with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_obj_of_another_advisor_returns_404(self):
        obj_id = self._create_obj_of_another_advisor()
        response = self._update(obj_id, data=self._get_data_after_update())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_delete(self):
        obj_id = self._create_obj()
        response = self._delete(obj_id=obj_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(), 0)

    def test_delete_without_auth_returns_401(self):
        obj_id = self._create_obj()
        self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(), 1)
        response = self._delete(obj_id=obj_id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(), 1)

    def test_delete_obj_of_another_advisor_returns_404(self):
        obj_id = self._create_obj_of_another_advisor()
        response = self._delete(obj_id=obj_id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(self.tested_model.objects.filter(id=obj_id).exists())

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_modifying_object_if_it_was_submitted_to_encompass_returns_405(self):
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        obj_id = self._create_obj()
        response = self._update(obj_id, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._delete(obj_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_object_creation_if_owner_does_not_exist_returns_404(self):
        # pylint: disable=protected-access
        self.borrower._meta.model.objects.filter(id=self.borrower.id).delete()
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_object_creation_maximum(self):
        # a bit of klugery
        args = ([self.borrower.borrower.loan_profile.id, self.borrower.borrower.id, self.borrower.id]
                if self.is_coborrower
                else [self.borrower.loan_profile.id, self.borrower.id])
        view_func = resolve(reverse(self.url_list, args=args)).func
        view_module = importlib.import_module(view_func.__module__)
        view = getattr(view_module, view_func.__name__)
        self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(), 0)
        for idx in range(view.instance_count_maximum):
            response = self._create()
            self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(), 1+idx)
            self.assertTrue(getattr(self.borrower, self.tested_model_rel_name).count() <=
                            view.instance_count_maximum)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(getattr(self.borrower, self.tested_model_rel_name).count(),
                         view.instance_count_maximum)


class BorrowerPropertyViewTestMixin(AdvisorCRUDTestMixin):
    url = None
    tested_model = None
    tested_model_related_name = None

    def _create(self, data=None, with_auth=True):
        return self.client.post(
            reverse(self.url, args=self.args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _retrieve(self, with_auth=True):
        return self.client.get(
            reverse(self.url, args=self.args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _update(self, data=None, with_auth=True):
        return self.client.patch(
            reverse(self.url, args=self.args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _delete(self, with_auth=True):
        return self.client.delete(
            reverse(self.url, args=self.args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _get_related_obj(self):
        raise NotImplementedError()

    def _create_related_obj(self, data=None):
        raise NotImplementedError()

    def _get_obj_data_before_update(self):
        raise NotImplementedError()

    def _get_obj_data_after_update(self):
        raise NotImplementedError()

    def test_successful_create(self):
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.tested_model.objects.filter(**{self.tested_model_related_name: self.borrower}).exists())

    def test_creation_without_auth_returns_401(self):
        response = self._create(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_retrieve(self):
        self._create_related_obj()
        response = self._retrieve()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_in_case_of_inactive_borrower_returns_403(self):
        self._create_related_obj()
        try:
            self.borrower.is_active = False
            self.borrower.save()
            response = self._retrieve()
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        finally:
            self.borrower.is_active = True
            self.borrower.save()

    @unittest.skip("This scenario is not working for views-properties")
    def test_retrieve_obj_of_another_advisor_returns_404(self):
        pass

    def test_retrieve_without_auth_returns_401(self):
        self._create_related_obj()
        response = self._retrieve(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_update(self):
        self._create_related_obj(data=self._get_obj_data_before_update())
        data = self._get_obj_data_after_update()
        response = self._update(data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(getattr(self._get_related_obj(), data.keys()[0]), data.values()[0])

    def test_update_without_auth_returns_401(self):
        data = self._get_obj_data_before_update()
        self._create_related_obj(data=self._get_obj_data_before_update())
        response = self._update(data=self._get_obj_data_after_update(), with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(getattr(self._get_related_obj(), data.keys()[0]), data.values()[0])

    @unittest.skip("This scenario is not working for views-properties")
    def test_update_obj_of_another_advisor_returns_404(self):
        pass

    def test_successful_delete(self):
        self._create_related_obj()
        response = self._delete()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        related_obj = self._get_related_obj()
        self.assertIsNone(related_obj)

    def test_delete_without_auth_returns_401(self):
        self._create_related_obj()
        response = self._delete(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        related_obj = self._get_related_obj()
        self.assertIsNotNone(related_obj)

    @unittest.skip("This scenario is not working for views-properties")
    def test_delete_obj_of_another_advisor_returns_404(self):
        pass

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_modifying_object_if_it_was_submitted_to_encompass_returns_405(self):
        self._create_related_obj()
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._update()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._delete()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_object_creation_if_owner_does_not_exist_returns_404(self):
        # pylint: disable=protected-access
        self.borrower._meta.model.objects.filter(id=self.borrower.id).delete()
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HoldingAssetsOwnerMixin(object):
    """
    Mixin used to test transferring ownership
    of asset from borrower to coborrower and
    vice-versa.
    """

    def _put(self, obj_id, data=None, with_auth=True):
        if self.is_coborrower:
            args = [
                self.borrower.borrower.loan_profile.id,
                self.borrower.borrower.id,
                self.borrower.id,
                obj_id
            ]
        else:
            args = [self.borrower.loan_profile.id, self.borrower.id, obj_id, ]

        return self.client.put(
            reverse(self.url_detail, args=args),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def test_successful_change_owner_of_asset(self):
        raise NotImplementedError()

    def test_assigning_asset_to_borrower_of_another_advisor_returns_400(self):
        raise NotImplementedError()


##############
# MAIN VIEWS #
##############


# pylint: disable=R0904
class TestAdvisorLoanProfileV1View(AdvisorAPITestCase, AdvisorCRUDTestMixin):
    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.loggers = {}
        self.loggers = {logging.getLogger(name): logging.getLogger(name).level
                        for name in ("sample.loans.models",
                                     "sample.encompass.synchronization")}
        for logger in self.loggers:
            logger.setLevel(logging.WARN)

    def tearDown(self):
        for logger, level in self.loggers.items():
            logger.setLevel(level)

    def _create(self, data=None, with_auth=True):
        return self.client.post(
            reverse('advisor-portal:loanprofilev1-list'),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _retrieve(self, loanprofile_id, with_auth=True):
        return self.client.get(
            reverse('advisor-portal:loanprofilev1-detail', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _update(self, loanprofile_id, data=None, with_auth=True):
        return self.client.patch(
            reverse('advisor-portal:loanprofilev1-detail', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _delete(self, loanprofile_id, with_auth=True):
        return self.client.delete(
            reverse('advisor-portal:loanprofilev1-detail', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _los_guid(self, loanprofile_id, with_auth=True):
        return self.client.post(
            reverse('advisor-portal:loanprofilev1-los-guid', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _confirm_demographics_questions(self, loanprofile_id, with_auth=True):
        return self.client.post(
            reverse('advisor-portal:loanprofilev1-confirm-demographics-questions', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _storage(self, loanprofile_id, with_auth=True):
        return self.client.post(
            reverse('advisor-portal:loanprofilev1-storage', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _new_property_address(self, loanprofile_id, with_auth=True):
        return self.client.post(
            reverse('advisor-portal:loanprofilev1-new-property-address', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _trigger_respa(self, loanprofile_id, with_auth=True):
        return self.client.patch(
            reverse('advisor-portal:loanprofilev1-trigger-respa', args=[loanprofile_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def test_successful_create(self):
        self.assertEqual(LoanProfileV1.objects.filter(advisor=self.user).count(), 0)
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['source'], 'advisor_portal')
        self.assertEqual(LoanProfileV1.objects.filter(advisor=self.user).count(), 1)

    def test_creation_without_auth_returns_401(self):
        response = self._create(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_retrieve(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        response = self._retrieve(lp.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_without_auth_returns_401(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        response = self._retrieve(lp.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_obj_of_another_advisor_returns_404(self):
        lp = loan_factories.LoanProfileV1Factory()
        response = self._retrieve(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_update(self):
        lp = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
            purpose_of_loan='purchase',
        )
        response = self._update(lp.id, data={'purposeOfLoan': 'refinance'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(LoanProfileV1.objects.get(id=lp.id).purpose_of_loan, 'refinance')

    def test_update_without_auth_returns_401(self):
        lp = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
        )
        response = self._update(lp.id, data={'purposeOfLoan': 'refinance'}, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_obj_of_another_advisor_returns_404(self):
        lp = loan_factories.LoanProfileV1Factory()
        response = self._update(lp.id, data={'purposeOfLoan': 'refinance'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_delete(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        self.assertTrue(lp.is_active)
        response = self._delete(lp.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LoanProfileV1.objects.get(id=lp.id).is_active)

    def test_delete_without_auth_returns_401(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        response = self._delete(lp.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_obj_of_another_advisor_returns_404(self):
        lp = loan_factories.LoanProfileV1Factory()
        response = self._delete(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('storage.models.StorageManager.get_or_create_loan_profile_storage')
    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_successful_storage_creation(self, mocked_manager):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        loan_factories.BorrowerV1Factory(loan_profile=lp)
        mocked_manager.return_value = storage_factories.StorageFactory(
            storage_id='test666',
            name='test',
            role='test',
        )
        response = self._storage(lp.id)
        self.assertTrue(mocked_manager.called)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id'], 'test666')
        updated_lp = LoanProfileV1.objects.get(id=lp.id)
        self.assertEqual(updated_lp.storage.storage_id, "test666")

    @mock.patch('storage.models.StorageManager.get_or_create_loan_profile_storage')
    def test_unsuccessful_storage_creation_returns_400(self, mocked_manager):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        loan_factories.BorrowerV1Factory(loan_profile=lp)
        mocked_manager.return_value = None
        response = self._storage(lp.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        updated_lp = LoanProfileV1.objects.get(id=lp.id)
        self.assertEqual(updated_lp.storage_id, None)

    def test_storage_creation_for_another_advisor_returns_401(self):
        lp = loan_factories.LoanProfileV1Factory()
        loan_factories.BorrowerV1Factory(loan_profile=lp)
        response = self._storage(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_storage_creation_without_auth_returns_401(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        loan_factories.BorrowerV1Factory(loan_profile=lp)
        response = self._storage(lp.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_los_guid_creation_if_never_synced(self):
        lp = loan_factories.PurchaseLoanProfileFactory(
            advisor=self.user,
            encompass_sync_status=LoanProfileV1.ENCOMPASS_NEVER_SYNCED,
        )
        self.assertTrue(lp.can_sync_to_encompass())
        response = self._los_guid(lp.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["request_submitted"], True)
        updated_lp = LoanProfileV1.objects.get(id=lp.id)
        self.assertTrue(updated_lp.can_sync_to_encompass())
        self.assertEqual(updated_lp.encompass_sync_status, LoanProfileV1.ENCOMPASS_READY_TO_SYNC)

    def test_successful_los_guid_creation_if_sync_failed(self):
        lp = loan_factories.PurchaseLoanProfileFactory(
            advisor=self.user,
            encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNC_FAILED,
        )
        response = self._los_guid(lp.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["request_submitted"], True)
        updated_lp = LoanProfileV1.objects.get(id=lp.id)
        self.assertTrue(updated_lp.can_sync_to_encompass())
        self.assertEqual(updated_lp.encompass_sync_status, LoanProfileV1.ENCOMPASS_READY_TO_SYNC)

    def test_unsuccessful_los_guid_creation_returns_400(self):
        lp = loan_factories.RefinanceOtherLoanProfileFactory(advisor=self.user)
        self.assertTrue(lp.can_sync_to_encompass(Exception))
        with mock.patch('loans.models.LoanProfileV1.save') as mocked_save:
            mocked_save.side_effect = Exception('')
            response = self._los_guid(lp.id)
        updated_lp = LoanProfileV1.objects.get(id=lp.id)
        self.assertTrue(updated_lp.can_sync_to_encompass())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(updated_lp.encompass_sync_status, LoanProfileV1.ENCOMPASS_NEVER_SYNCED)

    def test_los_guid_creation_for_another_advisor_returns_404(self):
        lp = loan_factories.LoanProfileV1Factory()
        loan_factories.BorrowerV1Factory(loan_profile=lp)
        response = self._los_guid(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_los_guid_creation_without_auth_returns_401(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        loan_factories.BorrowerV1Factory(loan_profile=lp)
        response = self._los_guid(lp.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_los_guid_creation_of_wrong_sync_status_lp_returns_400(self):
        lp = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
            encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNCED,
        )
        response = self._los_guid(lp.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        updated_lp = LoanProfileV1.objects.get(id=lp.id)
        self.assertEqual(updated_lp.encompass_sync_status, LoanProfileV1.ENCOMPASS_SYNCED)

    def test_successful_confirm_of_demographics_questions(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        self.assertIsNone(lp.is_demographics_questions_request_confirmed)
        response = self._confirm_demographics_questions(lp.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        updated_lp = LoanProfileV1.objects.get(id=lp.id)
        self.assertTrue(updated_lp.is_demographics_questions_request_confirmed)

    def test_confirm_of_demographics_questions_for_another_advisor_returns_404(self):
        lp = loan_factories.LoanProfileV1Factory()
        response = self._confirm_demographics_questions(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_confirm_of_demographics_questions_without_auth_returns_401(self):
        lp = loan_factories.LoanProfileV1Factory(advisor=self.user)
        response = self._confirm_demographics_questions(lp.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_modifying_object_if_it_was_submitted_to_encompass_returns_405(self):
        lp = loan_factories.LoanProfileV1EncompassSyncedFactory(advisor=self.user)
        response = self._update(lp.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._delete(lp.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_modifying_object_if_it_is_encompass_ready_for_sync_returns_404(self):
        lp = loan_factories.LoanProfileV1Factory(
            encompass_sync_status=LoanProfileV1.ENCOMPASS_READY_TO_SYNC,
            advisor=self.user,
        )
        response = self._update(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self._delete(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_modifying_object_if_it_is_encompass_sync_in_progress_returns_404(self):
        lp = loan_factories.LoanProfileV1Factory(
            encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNC_IN_PROGRESS,
            advisor=self.user,
        )
        response = self._update(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self._delete(lp.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_object_creation_if_owner_does_not_exist_returns_404(self):
        response = self._new_property_address(123)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_trigger_respa(self):
        lp = loan_factories.PurchaseLoanProfileFactory(
            advisor=self.user,
        )

        loan_factories.BorrowerV1Factory(
            loan_profile=lp,
            ssn='666121234',
            income=[
                loan_factories.BaseIncomeFactory(value='123')
            ],
        )
        response = self._trigger_respa(lp.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unsuccessful_trigger_respa_returns_400(self):
        lp = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
        )
        loan_factories.BorrowerV1Factory(
            loan_profile=lp,
            ssn='666121234',
            income=[
                loan_factories.BaseIncomeFactory(value='123')
            ],
        )
        response = self._trigger_respa(lp.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

############
# BORROWER #
############


class TestAdvisorLoanProfileV1BorrowerV1View(AdvisorAPITestCase, AdvisorCRUDTestMixin):
    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.loanprofile = loan_factories.LoanProfileV1EncompassSyncedFactory()

    def _create(self, data=None, with_auth=True):
        return self.client.post(
            reverse('advisor-portal:loan-profiles-v1-borrowers-list', args=[self.loanprofile.id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _retrieve(self, borrower_id, with_auth=True):
        return self.client.get(
            reverse('advisor-portal:loan-profiles-v1-borrowers-detail', args=[self.loanprofile.id, borrower_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _update(self, borrower_id, data=None, with_auth=True):
        return self.client.patch(
            reverse('advisor-portal:loan-profiles-v1-borrowers-detail', args=[self.loanprofile.id, borrower_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _delete(self, borrower_id, with_auth=True):
        return self.client.delete(
            reverse('advisor-portal:loan-profiles-v1-borrowers-detail', args=[self.loanprofile.id, borrower_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def test_successful_create(self):
        self.assertEqual(
            BorrowerV1.objects.filter(loan_profile_id=self.loanprofile.id).count(),
            0
        )
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            BorrowerV1.objects.filter(loan_profile_id=self.loanprofile.id).count(),
            1
        )

    def test_creation_without_auth_returns_401(self):
        self.assertEqual(
            BorrowerV1.objects.filter(loan_profile_id=self.loanprofile.id).count(),
            0
        )
        response = self._create(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            BorrowerV1.objects.filter(loan_profile_id=self.loanprofile.id).count(),
            0
        )

    def test_successful_retrieve(self):
        borrower_obj = loan_factories.BorrowerV1Factory(loan_profile=self.loanprofile)
        response = self._retrieve(borrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_obj_of_another_advisor_returns_404(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        response = self._retrieve(borrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_without_auth_returns_401(self):
        borrower_obj = loan_factories.BorrowerV1Factory(loan_profile=self.loanprofile)
        response = self._retrieve(borrower_obj.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_update(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=self.loanprofile,
            first_name='Foo',
        )
        response = self._update(borrower_obj.id, data={'first_name': 'Bar'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BorrowerV1.objects.get(id=borrower_obj.id).first_name, 'Bar')

    def test_update_without_auth_returns_401(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=self.loanprofile,
        )
        response = self._update(borrower_obj.id, data={'first_name': 'Bar'}, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_obj_of_another_advisor_returns_404(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        response = self._update(borrower_obj.id, data={'first_name': 'Bar'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_delete(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=self.loanprofile,
        )
        self.assertTrue(borrower_obj.is_active)
        response = self._delete(borrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BorrowerV1.objects.get(id=borrower_obj.id).is_active)

    def test_delete_without_auth_returns_401(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=self.loanprofile,
        )
        response = self._delete(borrower_obj.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_obj_of_another_advisor_returns_404(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        response = self._delete(borrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_modifying_object_if_it_was_submitted_to_encompass_returns_405(self):
        borrower_obj = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._update(borrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._delete(borrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_object_creation_if_owner_does_not_exist_returns_404(self):
        # pylint: disable=protected-access
        self.loanprofile._meta.model.objects.filter(id=self.loanprofile.id).delete()
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestAdvisorLoanProfileV1BorrowerV1MailingAddress(AdvisorAPITestCase, BorrowerPropertyViewTestMixin):
    url = 'advisor-portal:loan-profiles-v1-borrowers-mailing-address'
    tested_model = AddressV1
    tested_model_related_name = 'borrowerv1_mailing_address'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory(
                advisor=self.user,
            )
        )
        self.args = [self.borrower.loan_profile.id, self.borrower.id, ]

    def _get_related_obj(self):
        borrower = BorrowerV1.objects.get(id=self.borrower.id)
        return borrower.mailing_address

    def _create_related_obj(self, data=None):
        if data:
            self.borrower.mailing_address = loan_factories.AddressV1Factory(**data)
        else:
            self.borrower.mailing_address = loan_factories.AddressV1Factory()
        self.borrower.save()

    def _get_obj_data_before_update(self):
        return {'street': 'Piccadilly str'}

    def _get_obj_data_after_update(self):
        return {'street': 'Baker str'}


class TestAdvisorLoanProfileV1BorrowerV1Demographics(AdvisorAPITestCase, BorrowerPropertyViewTestMixin):
    url = 'advisor-portal:loan-profiles-v1-borrowers-demographics'
    tested_model = DemographicsV1
    tested_model_related_name = 'borrowerv1'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory(
                advisor=self.user,
            )
        )
        self.args = [self.borrower.loan_profile.id, self.borrower.id, ]

    def _get_related_obj(self):
        borrower = BorrowerV1.objects.get(id=self.borrower.id)
        return borrower.demographics

    def _create_related_obj(self, data=None):
        if data:
            self.borrower.demographics = loan_factories.DemographicsV1Factory(**data)
        else:
            self.borrower.demographics = loan_factories.DemographicsV1Factory()
        self.borrower.save()

    def _get_obj_data_before_update(self):
        return {'owned_property_type': 'Test'}

    def _get_obj_data_after_update(self):
        return {'owned_property_type': 'Not test'}

    def test_patching_race_as_list_returns_200(self):
        self._create_related_obj()
        response = self._update(data={'race': ['White', 'Asian']})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patching_race_as_non_list_returns_400(self):
        self._create_related_obj()
        response = self._update(data={'race': 'White'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestAdvisorLoanProfileV1BorrowerV1Realtor(AdvisorAPITestCase, BorrowerPropertyViewTestMixin):
    url = 'advisor-portal:loan-profiles-v1-borrowers-realtor'
    tested_model = ContactV1
    tested_model_related_name = 'borrowerv1_realtor'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory(
                advisor=self.user,
            )
        )
        self.args = [self.borrower.loan_profile.id, self.borrower.id, ]

    def _get_related_obj(self):
        borrower = BorrowerV1.objects.get(id=self.borrower.id)
        return borrower.realtor

    def _create_related_obj(self, data=None):
        if data:
            self.borrower.realtor = loan_factories.ContactV1Factory(**data)
        else:
            self.borrower.realtor = loan_factories.ContactV1Factory()
        self.borrower.save()

    def _get_obj_data_before_update(self):
        return {'first_name': 'Bob'}

    def _get_obj_data_after_update(self):
        return {'first_name': 'Rob'}


class TestBorrowerPreviousAddressesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-previous-addresses-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-previous-addresses-detail'
    tested_model = AddressV1
    tested_model_rel_name = 'previous_addresses'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        address = loan_factories.AddressV1Factory()
        borrower.previous_addresses.add(address)
        borrower.save()
        return address.id

    def _create_obj(self):
        address = loan_factories.AddressV1Factory()
        self.borrower.previous_addresses.add(address)
        self.borrower.save()
        return address.id

    def _get_data_after_update(self):
        return {'street': 'Baker str'}


class TestBorrowerPreviousEmploymentsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-previous-employments-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-previous-employments-detail'
    tested_model = EmploymentV1
    tested_model_rel_name = 'previous_employment'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create(self, data=None, with_auth=True):
        if data is None:
            data = {'company_name': 'Bob & Rob CO.'}
        elif 'company_name' not in data:
            data['company_name'] = 'Bob & Rob CO.'
        return super(TestBorrowerPreviousEmploymentsView, self)._create(data, with_auth)

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        empl = loan_factories.EmploymentV1Factory()
        borrower.previous_employment.add(empl)
        borrower.save()
        return empl.id

    def _create_obj(self):
        empl = loan_factories.EmploymentV1Factory()
        self.borrower.previous_employment.add(empl)
        self.borrower.save()
        return empl.id

    def _get_data_after_update(self):
        return {'company_name': 'Bob & Rob CO.'}


class TestBorrowerHoldingAssetsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin, HoldingAssetsOwnerMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-holding-assets-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-holding-assets-detail'
    tested_model = HoldingAssetV1
    tested_model_rel_name = 'holding_assets'

    @staticmethod
    def _get_creation_data():
        return {'kind': HoldingAssetV1.AUTOMOBILE}

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.CheckingAccountFactory()
        borrower.holding_assets.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.FourOhOneKayAccountFactory()
        self.borrower.holding_assets.add(obj)
        self.borrower.save()
        return obj.id

    def _get_data_after_update(self):
        return {'current_value': 666}

    def test_successful_change_owner_of_asset(self):
        coborrower = loan_factories.CoborrowerV1Factory(borrower=self.borrower)
        asset_id = self._create_obj()
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), self.borrower)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), None)
        response = self._put(asset_id, data={'borrowerId': self.borrower.id, 'coborrowerId': coborrower.id})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), self.borrower)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), coborrower)
        response = self._put(asset_id, data={'coborrowerId': coborrower.id})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), None)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), coborrower)

    def test_assigning_asset_to_borrower_of_another_advisor_returns_400(self):
        coborrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        asset_id = self._create_obj()
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), self.borrower)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), None)
        response = self._put(asset_id, data={'borrowerId': coborrower.borrower.id, 'coborrowerId': coborrower.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), self.borrower)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), None)


class TestBorrowerVehicleAssetsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-vehicle-assets-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-vehicle-assets-detail'
    tested_model = VehicleAssetV1
    tested_model_rel_name = 'vehicle_assets'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.VehicleAssetV1Factory()
        borrower.vehicle_assets.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.VehicleAssetV1Factory()
        self.borrower.vehicle_assets.add(obj)
        self.borrower.save()
        return obj.id

    def _get_data_after_update(self):
        return {'model': 'Test'}


class TestBorrowerInsuranceAssetsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-insurance-assets-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-insurance-assets-detail'
    tested_model = InsuranceAssetV1
    tested_model_rel_name = 'insurance_assets'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.InsuranceAssetV1Factory()
        borrower.insurance_assets.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.InsuranceAssetV1Factory()
        self.borrower.insurance_assets.add(obj)
        self.borrower.save()
        return obj.id

    def _get_data_after_update(self):
        return {'value': 666}


class TestBorrowerIncomesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-incomes-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-incomes-detail'
    tested_model = IncomeV1
    tested_model_rel_name = 'income'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.IncomeV1Factory()
        borrower.income.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.IncomeV1Factory()
        self.borrower.income.add(obj)
        self.borrower.save()
        return obj.id

    @staticmethod
    def _get_creation_data():
        return {'kind': 'Other', 'value': 111}

    def _get_data_after_update(self):
        return {'value': 666, 'kind': 'Other'}

    def test_allowed_the_same_kinds(self):
        view = self._get_view()
        self.assertEqual(view.allowed_kinds, [IncomeV1.OTHER.lower()])

    def test_creation_with_kind_exists(self):
        data = {'kind': IncomeV1.BONUS, 'value': 111}
        response = self._create(data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self._create(data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Item with kind \'{}\' already exists.'.format(IncomeV1.BONUS)})


class TestBorrowerExpensesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-expenses-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-expenses-detail'
    tested_model = ExpenseV1
    tested_model_rel_name = 'expense'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.ExpenseV1Factory()
        borrower.expense.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.ExpenseV1Factory()
        self.borrower.expense.add(obj)
        self.borrower.save()
        return obj.id

    @staticmethod
    def _get_creation_data():
        return {'kind': 'Rent', 'value': 111}

    def _get_data_after_update(self):
        return {'value': 666, 'kind': 'Other'}

    def test_object_creation_maximum(self):
        kinds = [i[0] for i in ExpenseV1.EXPENSE_CHOICES]
        for kind in kinds:
            data = self._get_creation_data()
            data['kind'] = kind
            response = self._create(data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            response = self._create(data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data, {'detail': 'Item with kind \'{}\' already exists.'.format(kind)})


class TestBorrowerLiabilitiesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-borrowers-liabilities-list'
    url_detail = 'advisor-portal:loan-profiles-v1-borrowers-liabilities-detail'
    tested_model = LiabilityV1
    tested_model_rel_name = 'liabilities'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.BorrowerV1Factory(
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.RevolvingLiabilityFactory()
        borrower.liabilities.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self, data=None):
        factory_params = {} if data is None else data
        obj = loan_factories.TaxesLiabilityFactory(**factory_params)
        self.borrower.liabilities.add(obj)
        self.borrower.save()
        return obj.id

    @staticmethod
    def _get_creation_data():
        return {
            'holder_name': 'Test1',
            'kind': 'revolving',
            'account_identifier': '12345',
            'monthly_payment': 1000,
            'unpaid_balance': 1000,
            'months_remaining': 5,
            'comment': 'blah blah blah',
            'will_be_paid_off': True,
            'will_be_subordinated': True,
            'exclude_from_liabilities': False,
        }

    def _get_data_after_update(self):
        return {
            'holder_name': 'Test2',
            'kind': 'child_support',
            'account_identifier': '54321',
            'monthly_payment': 5000,
            'unpaid_balance': 5000,
            'months_remaining': 25,
            'comment': 'test test test',
            'will_be_paid_off': False,
            'will_be_subordinated': False,
            'exclude_from_liabilities': True,
        }

    def test_update_restricted_fields_if_object_is_not_editable_returns_400(self):
        data = self._get_creation_data()
        data['is_editable'] = False
        obj_id = self._create_obj(data)
        data = self._get_data_after_update()
        response = self._update(obj_id, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_update_non_restricted_fields_if_object_is_not_editable_returns_200(self):
        data = self._get_creation_data()
        data['is_editable'] = False
        obj_id = self._create_obj(data)
        data = {
            'id': obj_id,
            'comment': 'test blah blah',
            'will_be_paid_off': False,
            'will_be_subordinated': False,
            'exclude_from_liabilities': True,
        }
        response = self._update(obj_id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_id_if_object_is_not_editable_returns_400(self):
        data = self._get_creation_data()
        data['is_editable'] = False
        obj_id = self._create_obj(data)
        data = {
            'id': obj_id + 1,
            'comment': 'test blah blah',
        }
        response = self._update(obj_id, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


##############
# COBORROWER #
##############


class TestAdvisorLoanProfileV1CoborrowerV1View(AdvisorAPITestCase, AdvisorCRUDTestMixin):
    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.loanprofile = loan_factories.LoanProfileV1EncompassSyncedFactory()
        self.borrower = loan_factories.BorrowerV1Factory(loan_profile=self.loanprofile)

    def _create(self, data=None, with_auth=True):
        return self.client.post(
            reverse('advisor-portal:loan-profiles-v1-coborrowers-list',
                    args=[self.loanprofile.id, self.borrower.id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _retrieve(self, coborrower_id, with_auth=True):
        return self.client.get(
            reverse('advisor-portal:loan-profiles-v1-coborrowers-detail',
                    args=[self.loanprofile.id, self.borrower.id, coborrower_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def _update(self, coborrower_id, data=None, with_auth=True):
        return self.client.patch(
            reverse('advisor-portal:loan-profiles-v1-coborrowers-detail',
                    args=[self.loanprofile.id, self.borrower.id, coborrower_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
            data=data or {},
        )

    def _delete(self, coborrower_id, with_auth=True):
        return self.client.delete(
            reverse('advisor-portal:loan-profiles-v1-coborrowers-detail',
                    args=[self.loanprofile.id, self.borrower.id, coborrower_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def test_successful_create(self):
        self.assertEqual(
            CoborrowerV1.objects.filter(borrower=self.borrower).count(),
            0
        )
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            CoborrowerV1.objects.filter(borrower=self.borrower).count(),
            1
        )

    def test_successful_restore_of_inactive_object(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(borrower=self.borrower, is_active=False)
        self.assertEqual(
            CoborrowerV1.objects.filter(borrower=self.borrower).count(),
            1
        )
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            CoborrowerV1.objects.filter(borrower=self.borrower).count(),
            1
        )
        self.assertEqual(response.data['id'], coborrower_obj.id)

    def test_creation_without_auth_returns_401(self):
        self.assertEqual(
            CoborrowerV1.objects.filter(borrower=self.borrower).count(),
            0
        )
        response = self._create(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            CoborrowerV1.objects.filter(borrower=self.borrower).count(),
            0
        )

    def test_successful_retrieve(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(borrower=self.borrower)
        response = self._retrieve(coborrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_in_case_of_inactive_coborrower_returns_404(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower=self.borrower, is_active=False
        )
        response = self._retrieve(coborrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_obj_of_another_advisor_returns_404(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        response = self._retrieve(coborrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_without_auth_returns_401(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(borrower=self.borrower)
        response = self._retrieve(coborrower_obj.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_update(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower=self.borrower,
            borrower__loan_profile=self.loanprofile,
            first_name='Foo',
        )
        response = self._update(coborrower_obj.id, data={'first_name': 'Bar'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CoborrowerV1.objects.get(id=coborrower_obj.id).first_name, 'Bar')

    def test_update_without_auth_returns_401(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower=self.borrower,
            borrower__loan_profile=self.loanprofile,
        )
        response = self._update(coborrower_obj.id, data={'first_name': 'Bar'}, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_obj_of_another_advisor_returns_404(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        response = self._update(coborrower_obj.id, data={'first_name': 'Bar'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_delete(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower=self.borrower,
        )
        self.assertTrue(coborrower_obj.is_active)
        response = self._delete(coborrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CoborrowerV1.objects.get(id=coborrower_obj.id).is_active)

    def test_delete_without_auth_returns_401(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower=self.borrower,
        )
        response = self._delete(coborrower_obj.id, with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_obj_of_another_advisor_returns_404(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        response = self._delete(coborrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(ADVISOR_PORTAL_LOAN_PROFILE_MODIFYING_LIMITATION_ENABLED=True)
    def test_modifying_object_if_it_was_submitted_to_encompass_returns_405(self):
        coborrower_obj = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._update(coborrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self._delete(coborrower_obj.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_object_creation_if_owner_does_not_exist_returns_404(self):
        # pylint: disable=protected-access
        self.borrower._meta.model.objects.filter(id=self.borrower.id).delete()
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestAdvisorLoanProfileV1CoborrowerV1MailingAddress(AdvisorAPITestCase, BorrowerPropertyViewTestMixin):
    url = 'advisor-portal:loan-profiles-v1-coborrowers-mailing-address'
    tested_model = AddressV1
    tested_model_related_name = 'coborrowerv1_mailing_address'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory(
                advisor=self.user,
            )
        )
        self.args = [self.borrower.borrower.loan_profile.id, self.borrower.borrower.id, self.borrower.id]

    def _get_related_obj(self):
        coborrower = CoborrowerV1.objects.get(id=self.borrower.id)
        return coborrower.mailing_address

    def _create_related_obj(self, data=None):
        if data:
            self.borrower.mailing_address = loan_factories.AddressV1Factory(**data)
        else:
            self.borrower.mailing_address = loan_factories.AddressV1Factory()
        self.borrower.save()

    def _get_obj_data_before_update(self):
        return {'street': 'Piccadilly str'}

    def _get_obj_data_after_update(self):
        return {'street': 'Baker str'}


class TestAdvisorLoanProfileV1CoborrowerV1Demographics(AdvisorAPITestCase, BorrowerPropertyViewTestMixin):
    url = 'advisor-portal:loan-profiles-v1-coborrowers-demographics'
    tested_model = DemographicsV1
    tested_model_related_name = 'coborrowerv1'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory(
                advisor=self.user,
            )
        )
        self.args = [self.borrower.borrower.loan_profile.id, self.borrower.borrower.id, self.borrower.id]

    def _get_related_obj(self):
        coborrower = CoborrowerV1.objects.get(id=self.borrower.id)
        return coborrower.demographics

    def _create_related_obj(self, data=None):
        if data:
            self.borrower.demographics = loan_factories.DemographicsV1Factory(**data)
        else:
            self.borrower.demographics = loan_factories.DemographicsV1Factory()
        self.borrower.save()

    def _get_obj_data_before_update(self):
        return {'owned_property_type': 'Test'}

    def _get_obj_data_after_update(self):
        return {'owned_property_type': 'Not test'}

    def test_patching_race_as_list_returns_200(self):
        self._create_related_obj()
        response = self._update(data={'race': ['White', 'Asian']})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patching_race_as_non_list_returns_400(self):
        self._create_related_obj()
        response = self._update(data={'race': 'Asian'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestAdvisorLoanProfileV1CoborrowerV1Realtor(AdvisorAPITestCase, BorrowerPropertyViewTestMixin):
    url = 'advisor-portal:loan-profiles-v1-coborrowers-realtor'
    tested_model = ContactV1
    tested_model_related_name = 'coborrowerv1_realtor'

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory(
                advisor=self.user,
            )
        )
        self.args = [self.borrower.borrower.loan_profile.id, self.borrower.borrower.id, self.borrower.id]

    def _get_related_obj(self):
        coborrower = CoborrowerV1.objects.get(id=self.borrower.id)
        return coborrower.realtor

    def _create_related_obj(self, data=None):
        if data:
            self.borrower.realtor = loan_factories.ContactV1Factory(**data)
        else:
            self.borrower.realtor = loan_factories.ContactV1Factory()
        self.borrower.save()

    def _get_obj_data_before_update(self):
        return {'first_name': 'Bob'}

    def _get_obj_data_after_update(self):
        return {'first_name': 'Rob'}


class TestCoborrowerPreviousAddressesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-previous-addresses-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-previous-addresses-detail'
    tested_model = AddressV1
    tested_model_rel_name = 'previous_addresses'

    is_coborrower = True

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        address = loan_factories.AddressV1Factory()
        borrower.previous_addresses.add(address)
        borrower.save()
        return address.id

    def _create_obj(self):
        address = loan_factories.AddressV1Factory()
        self.borrower.previous_addresses.add(address)
        self.borrower.save()
        return address.id

    def _get_data_after_update(self):
        return {'street': 'Baker str'}


class TestCoborrowerPreviousEmploymentsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-previous-employments-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-previous-employments-detail'
    tested_model = EmploymentV1
    tested_model_rel_name = 'previous_employment'

    is_coborrower = True

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        empl = loan_factories.EmploymentV1Factory()
        borrower.previous_employment.add(empl)
        borrower.save()
        return empl.id

    def _create_obj(self):
        empl = loan_factories.EmploymentV1Factory()
        self.borrower.previous_employment.add(empl)
        self.borrower.save()
        return empl.id

    def _get_data_after_update(self):
        return {'company_name': 'Bob & Rob CO.'}


class TestCoborrowerHoldingAssetsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin, HoldingAssetsOwnerMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-holding-assets-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-holding-assets-detail'
    tested_model = HoldingAssetV1
    tested_model_rel_name = 'holding_assets'

    is_coborrower = True

    @staticmethod
    def _get_creation_data():
        return {'kind': HoldingAssetV1.AUTOMOBILE}

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.CodAccountFactory()
        borrower.holding_assets.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.IraAccountFactory()
        self.borrower.holding_assets.add(obj)
        self.borrower.save()
        return obj.id

    def _get_data_after_update(self):
        return {'current_value': 666}

    def test_successful_change_owner_of_asset(self):
        asset_id = self._create_obj()
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), None)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), self.borrower)
        response = self._put(asset_id, data={'borrowerId': self.borrower.borrower.id, 'coborrowerId': self.borrower.id})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), self.borrower.borrower)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), self.borrower)
        response = self._put(asset_id, data={'coborrowerId': self.borrower.id})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), None)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), self.borrower)

    def test_assigning_asset_to_borrower_of_another_advisor_returns_400(self):
        coborrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        asset_id = self._create_obj()
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), None)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), self.borrower)
        response = self._put(asset_id, data={'borrowerId': self.borrower.id, 'coborrowerId': coborrower.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).borrowerv1.first(), None)
        self.assertEqual(HoldingAssetV1.objects.get(id=asset_id).coborrowerv1.first(), self.borrower)


class TestCoborrowerVehicleAssetsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-vehicle-assets-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-vehicle-assets-detail'
    tested_model = VehicleAssetV1
    tested_model_rel_name = 'vehicle_assets'

    is_coborrower = True

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.VehicleAssetV1Factory()
        borrower.vehicle_assets.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.VehicleAssetV1Factory()
        self.borrower.vehicle_assets.add(obj)
        self.borrower.save()
        return obj.id

    def _get_data_after_update(self):
        return {'model': 'Test'}


class TestCoborrowerInsuranceAssetsView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-insurance-assets-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-insurance-assets-detail'
    tested_model = InsuranceAssetV1
    tested_model_rel_name = 'insurance_assets'

    is_coborrower = True

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.InsuranceAssetV1Factory()
        borrower.insurance_assets.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.InsuranceAssetV1Factory()
        self.borrower.insurance_assets.add(obj)
        self.borrower.save()
        return obj.id

    def _get_data_after_update(self):
        return {'value': 666}


class TestCoborrowerIncomesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-incomes-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-incomes-detail'
    tested_model = IncomeV1
    tested_model_rel_name = 'income'

    is_coborrower = True

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.IncomeV1Factory()
        borrower.income.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.IncomeV1Factory()
        self.borrower.income.add(obj)
        self.borrower.save()
        return obj.id

    @staticmethod
    def _get_creation_data():
        return {'kind': 'Other', 'value': 111}

    def _get_data_after_update(self):
        return {'value': 666, 'kind': 'Other'}

    def test_allowed_the_same_kinds(self):
        view = self._get_view()
        self.assertEqual(view.allowed_kinds, [IncomeV1.OTHER.lower()])

    def test_creation_with_kind_exists(self):
        data = {'kind': IncomeV1.BONUS, 'value': 111}
        response = self._create(data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self._create(data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'detail': 'Item with kind \'{}\' already exists.'.format(IncomeV1.BONUS)})


class TestCoborrowerExpensesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-expenses-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-expenses-detail'
    tested_model = ExpenseV1
    tested_model_rel_name = 'expense'

    is_coborrower = True

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.ExpenseV1Factory()
        borrower.expense.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self):
        obj = loan_factories.ExpenseV1Factory()
        self.borrower.expense.add(obj)
        self.borrower.save()
        return obj.id

    @staticmethod
    def _get_creation_data():
        return {'kind': 'Rent', 'value': 111}

    def _get_data_after_update(self):
        return {'value': 666, 'kind': 'Other'}

    def test_object_creation_maximum(self):
        kinds = [i[0] for i in ExpenseV1.EXPENSE_CHOICES]
        for kind in kinds:
            data = self._get_creation_data()
            data['kind'] = kind
            response = self._create(data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            response = self._create(data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data, {'detail': 'Item with kind \'{}\' already exists.'.format(kind)})


class TestCoborrowerLiabilitiesView(AdvisorAPITestCase, BorrowerResourceViewTestMixin):
    url_list = 'advisor-portal:loan-profiles-v1-coborrowers-liabilities-list'
    url_detail = 'advisor-portal:loan-profiles-v1-coborrowers-liabilities-detail'
    tested_model = LiabilityV1
    tested_model_rel_name = 'liabilities'

    is_coborrower = True

    @staticmethod
    def _get_creation_data():
        return {
            'holder_name': 'Test1',
            'kind': 'revolving',
            'account_identifier': '12345',
            'monthly_payment': 1000,
            'unpaid_balance': 1000,
            'months_remaining': 5,
            'comment': 'blah blah blah',
            'will_be_paid_off': True,
            'will_be_subordinated': True,
            'exclude_from_liabilities': False,
        }

    def _get_data_after_update(self):
        return {
            'holder_name': 'Test2',
            'kind': 'child_support',
            'account_identifier': '54321',
            'monthly_payment': 5000,
            'unpaid_balance': 5000,
            'months_remaining': 25,
            'comment': 'test test test',
            'will_be_paid_off': False,
            'will_be_subordinated': False,
            'exclude_from_liabilities': True,
        }

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1EncompassSyncedFactory()
        )

    def _create_obj_of_another_advisor(self):
        borrower = loan_factories.CoborrowerV1Factory(
            borrower__loan_profile=loan_factories.LoanProfileV1Factory()
        )
        obj = loan_factories.Open30DaysChargeAccountLiabilityFactory()
        borrower.liabilities.add(obj)
        borrower.save()
        return obj.id

    def _create_obj(self, data=None):
        factory_params = {} if data is None else data
        obj = loan_factories.LeasePaymentsLiabilityFactory(**factory_params)
        self.borrower.liabilities.add(obj)
        self.borrower.save()
        return obj.id

    @staticmethod
    def _get_creation_data():
        return {
            'holder_name': 'Test1',
            'kind': 'revolving',
            'account_identifier': '12345',
            'monthly_payment': 1000,
            'unpaid_balance': 1000,
            'months_remaining': 5,
            'comment': 'blah blah blah',
            'will_be_paid_off': True,
            'will_be_subordinated': True,
            'exclude_from_liabilities': False,
        }

    def _get_data_after_update(self):
        return {
            'holder_name': 'Test2',
            'kind': 'child_support',
            'account_identifier': '54321',
            'monthly_payment': 5000,
            'unpaid_balance': 5000,
            'months_remaining': 25,
            'comment': 'test test test',
            'will_be_paid_off': False,
            'will_be_subordinated': False,
            'exclude_from_liabilities': True,
        }

    def test_update_restricted_fields_if_object_is_not_editable_returns_400(self):
        obj_id = self._create_obj(data={'is_editable': False})
        data = self._get_data_after_update()
        response = self._update(obj_id, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_update_non_restricted_fields_if_object_is_not_editable_returns_200(self):
        obj_id = self._create_obj(data={'is_editable': False})
        data = {
            'id': obj_id,
            'comment': 'test blah blah',
            'will_be_paid_off': False,
            'will_be_subordinated': False,
            'exclude_from_liabilities': True,
        }
        response = self._update(obj_id, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_id_if_object_is_not_editable_returns_400(self):
        obj_id = self._create_obj(data={'is_editable': False})
        data = {
            'id': obj_id + 1,
            'comment': 'test blah blah',
        }
        response = self._update(obj_id, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestConcurrentUpdate(TransactionTestCase):
    """
    This test case describes how API will work
    if some object will be selected for update.
    """

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)
        self.borrower = loan_factories.BorrowerV1Factory(
            referral='unedited',
            loan_profile=loan_factories.LoanProfileV1Factory()
        )
        new_connections = ConnectionHandler(settings.DATABASES)
        self.new_connection = new_connections[DEFAULT_DB_ALIAS]

    def tearDown(self):
        self.end_blocking_transaction()
        self.new_connection.close()

    def end_blocking_transaction(self):
        # Roll back the blocking transaction.
        self.new_connection.rollback()
        self.new_connection.set_autocommit(True)

    def _get_jwt_auth(self):
        from rest_framework_jwt import utils
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)
        return 'JWT {0}'.format(token)

    def _update(self, borrower_id, data):
        return self.client.patch(
            reverse('advisor-portal:loan-profiles-v1-borrowers-detail',
                    args=[self.borrower.loan_profile.id, borrower_id]),
            HTTP_AUTHORIZATION=self._get_jwt_auth(),
            HTTP_X_FOR_UPDATE=True,
            content_type='application/json',
            data=data,
        )

    @db_connection_close
    def update_borrower(self):
        return self._update(borrower_id=self.borrower.id, data='{"referral": "parallel_request"}')

    def test_update_blocked_object(self):
        self.new_connection.set_autocommit(False)
        self.assertEqual(BorrowerV1.objects.get(id=self.borrower.id).referral, 'unedited')
        # Start a blocking transaction. At some point,
        # end_blocking_transaction() should be called.
        blocked_cursor = self.new_connection.cursor()
        # pylint: disable=protected-access
        sql = "SELECT * FROM %(db_table)s %(for_update)s;" % {
            'db_table': BorrowerV1._meta.db_table,
            'for_update': self.new_connection.ops.for_update_sql(),
        }
        blocked_cursor.execute(sql)
        # Need to run update on this borrower object in another thread
        # to emulate parallel request.
        # At this point it should wait for lock which was set above
        # and will update it there.
        thread = threading.Thread(target=self.update_borrower)
        thread.start()
        # pylint: disable=protected-access
        blocked_cursor.execute(
            "UPDATE %(db_table)s SET referral = 'blocked_transaction';" % {
                'db_table': BorrowerV1._meta.db_table,
            }
        )
        self.new_connection.commit()
        self.assertEqual(BorrowerV1.objects.get(id=self.borrower.id).referral, 'blocked_transaction')
        self.end_blocking_transaction()
        # If transaction above will not commit, thread join
        # will hang because object is selected for update.
        thread.join()
        self.assertEqual(BorrowerV1.objects.get(id=self.borrower.id).referral, 'parallel_request')


class TestMailingAddressConcurrentUpdateAndCreate(TransactionTestCase):
    """
    Asana: #46972649873909
    Concurrent requests on borrower and mailing address
    (which is using borrower object inside) can cause some
    race condition troubles.
    """

    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

        self.loanprofile = loan_factories.LoanProfileV1Factory()
        self.borrower = loan_factories.BorrowerV1Factory(loan_profile=self.loanprofile)

    def get_jwt_auth(self):
        from rest_framework_jwt import utils
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)
        return 'JWT {0}'.format(token)

    def _update_borrower(self, borrower_id, data):
        return self.client.patch(
            reverse('advisor-portal:loan-profiles-v1-borrowers-detail',
                    args=[self.loanprofile.id, borrower_id]),
            HTTP_AUTHORIZATION=self.get_jwt_auth(),
            HTTP_X_FOR_UPDATE=True,
            content_type='application/json',
            data=data,
        )

    def _create_mailing_address(self, data):
        return self.client.post(
            reverse('advisor-portal:loan-profiles-v1-borrowers-mailing-address',
                    args=[self.borrower.loan_profile.id, self.borrower.id, ]),
            HTTP_AUTHORIZATION=self.get_jwt_auth(),
            HTTP_X_FOR_UPDATE=True,
            content_type='application/json',
            data=data,
        )

    @db_connection_close()
    def execute_create_mailing_address(self):
        self._create_mailing_address(data={})

    @db_connection_close
    def execute_update_borrower(self):
        self._update_borrower(self.borrower.id, data='{"isMailingAddressSame": false}')

    def test_concurrent_update(self):
        thread1 = threading.Thread(target=self.execute_update_borrower)
        thread1.start()
        thread2 = threading.Thread(target=self.execute_create_mailing_address)
        thread2.start()
        thread1.join()
        thread2.join()
        self.assertFalse(BorrowerV1.objects.get(id=self.borrower.id).is_mailing_address_same)


class TestAdvisorLoanProfileV1SyncInProgressView(AdvisorAPITestCase):
    def setUp(self):
        self.user = accounts_factories.AdvisorFactory()
        self.client.login(username=self.user.username, password=accounts_factories.USER_PASSWORD)

    def _retrieve_list(self, with_auth=True):
        return self.client.get(
            reverse('advisor-portal:loanprofilev1-sync-in-progress-list'),
            HTTP_AUTHORIZATION=self.get_jwt_auth() if with_auth else '',
        )

    def test_successful_retrieve(self):
        lp = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
        )
        loan_factories.BorrowerV1Factory(
            loan_profile=lp,
            first_name="Kate",
            last_name="Hernandez",
            email="Kate.Hernandez1@example.com",
        )
        lp2 = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
            encompass_sync_status=LoanProfileV1.ENCOMPASS_READY_TO_SYNC,
        )
        b2 = loan_factories.BorrowerV1Factory(
            loan_profile=lp2,
            first_name="Kate",
            last_name="Hernandez",
            email="Kate.Hernandez2@example.com",
        )
        lp3 = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
            encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNC_IN_PROGRESS,
        )
        b3 = loan_factories.BorrowerV1Factory(
            loan_profile=lp3,
            first_name="Kate",
            last_name="Hernandez",
            email="Kate.Hernandez3@example.com",
        )
        lp4 = loan_factories.LoanProfileV1Factory(
            advisor=self.user,
            encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNC_FAILED,
        )
        b4 = loan_factories.BorrowerV1Factory(
            loan_profile=lp4,
            first_name="Kate",
            last_name="Hernandez",
            email="Kate.Hernandez4@example.com",
        )
        expected_data = [
            {
                "borrowers": [
                    {"lastName": "Hernandez", "id": b4.id, "firstName": "Kate", "email": "Kate.Hernandez4@example.com"}
                ],
                "encompassSyncStatus": "SYNC_FAILED", "id": lp4.id,
            },
            {
                "borrowers": [
                    {"lastName": "Hernandez", "id": b3.id, "firstName": "Kate", "email": "Kate.Hernandez3@example.com"}
                ],
                "encompassSyncStatus": "SYNC_IN_PROGRESS", "id": lp3.id,
            },
            {
                "borrowers": [
                    {"lastName": "Hernandez", "id": b2.id, "firstName": "Kate", "email": "Kate.Hernandez2@example.com"}
                ],
                "encompassSyncStatus": "READY_TO_SYNC", "id": lp2.id,
            }
        ]
        response = self._retrieve_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = json.loads(response.content).get('results')
        self.assertEqual(len(results), len(expected_data))

    def test_retrieve_without_auth_returns_401(self):
        loan_factories.LoanProfileV1Factory(advisor=self.user)
        response = self._retrieve_list(with_auth=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
