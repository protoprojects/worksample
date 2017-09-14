import datetime
import mock

from django.utils.timezone import now

from core.tests import CeleryTaskTestCase
from core.utils import LogMutingTestMixinBase
from loans import factories as loans_factories
from loans.models import LoanProfileV1

from advisor_portal import tasks


class AdvisorPortalTasksMutingMixin(LogMutingTestMixinBase):
    log_names = ['sample.advisor_portal.tasks']


def get_los_guid(self):
    """
    Test helper to fail one task in some case
    and pass in others.
    """
    if self.id == LoanProfileV1.objects.last().id:
        return None
    return 123


class TestSyncLoanProfileWithEncompass(AdvisorPortalTasksMutingMixin, CeleryTaskTestCase):
    @staticmethod
    def _call_task():
        return tasks.sync_all_loan_profiles_with_encompass.delay()

    @staticmethod
    def _create_lp_ready_to_sync():
        return loans_factories.LoanProfileV1Factory(
            encompass_sync_status=LoanProfileV1.ENCOMPASS_READY_TO_SYNC
        )

    def assertEncompassSuccessfulSync(self, lp_id):
        self.assertEqual(
            LoanProfileV1.objects.get(id=lp_id).encompass_sync_status,
            LoanProfileV1.ENCOMPASS_SYNCED
        )

    def assertEncompassUnsuccessfulSync(self, lp_id):
        self.assertEqual(
            LoanProfileV1.objects.get(id=lp_id).encompass_sync_status,
            LoanProfileV1.ENCOMPASS_SYNC_FAILED
        )

    @mock.patch('loans.models.LoanProfileV1.los_sync')
    def test_successful_sync_of_all_loan_profiles(self, mocked_los_sync):
        mocked_los_sync.return_value = 111
        lp1 = self._create_lp_ready_to_sync()
        lp2 = self._create_lp_ready_to_sync()
        lp3 = self._create_lp_ready_to_sync()
        task_result = self._call_task()
        self.assertEqual(mocked_los_sync.call_count, 3)
        self.assertTrue(task_result.successful())
        self.assertEncompassSuccessfulSync(lp1.id)
        self.assertEncompassSuccessfulSync(lp2.id)
        self.assertEncompassSuccessfulSync(lp3.id)

    @mock.patch('loans.models.LoanProfileV1.los_sync')
    def test_unsuccessful_sync_of_all_loan_profiles(self, mocked_los_sync):
        mocked_los_sync.side_effect = Exception('Test exception')
        lp1 = self._create_lp_ready_to_sync()
        lp2 = self._create_lp_ready_to_sync()
        lp3 = self._create_lp_ready_to_sync()
        task_result = self._call_task()
        self.assertEqual(mocked_los_sync.call_count, 3)
        self.assertTrue(task_result.successful())  # main task should be successful anyway
        self.assertEncompassUnsuccessfulSync(lp1.id)
        self.assertEncompassUnsuccessfulSync(lp2.id)
        self.assertEncompassUnsuccessfulSync(lp3.id)

    def test_unsuccessful_sync_of_one_loan_profile(self):
        los_sync_copy = LoanProfileV1.los_sync
        try:
            lp1 = self._create_lp_ready_to_sync()
            lp2 = self._create_lp_ready_to_sync()
            lp3 = self._create_lp_ready_to_sync()
            LoanProfileV1.los_sync = get_los_guid
            task_result = self._call_task()
            self.assertTrue(task_result.successful())  # main task should be successful anyway
            self.assertEncompassSuccessfulSync(lp1.id)
            self.assertEncompassSuccessfulSync(lp2.id)
            self.assertEncompassUnsuccessfulSync(lp3.id)
        finally:
            LoanProfileV1.los_sync = los_sync_copy


class TestFindStaleInProgressLoanProfiles(AdvisorPortalTasksMutingMixin, CeleryTaskTestCase):
    @staticmethod
    def _call_task():
        return tasks.find_stale_in_progress_loan_profiles.delay()

    @staticmethod
    def _create_lp_in_progress(sent_datetime):
        return loans_factories.LoanProfileV1Factory(
            encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNC_IN_PROGRESS,
            datetime_sent_to_encompass=sent_datetime
        )

    def assertStatusUpdated(self, lp_id):
        self.assertEqual(
            LoanProfileV1.objects.get(id=lp_id).encompass_sync_status,
            LoanProfileV1.ENCOMPASS_READY_TO_SYNC
        )

    def assertStatusNotUpdated(self, lp_id):
        self.assertEqual(
            LoanProfileV1.objects.get(id=lp_id).encompass_sync_status,
            LoanProfileV1.ENCOMPASS_SYNC_IN_PROGRESS
        )

    def test_successful_change_of_status(self):
        lp1 = self._create_lp_in_progress(now() - datetime.timedelta(minutes=5))
        lp2 = self._create_lp_in_progress(now() - datetime.timedelta(minutes=10))
        lp3 = self._create_lp_in_progress(now() - datetime.timedelta(minutes=4, seconds=50))
        task_result = self._call_task()
        self.assertTrue(task_result.successful())
        self.assertStatusUpdated(lp1.id)
        self.assertStatusUpdated(lp2.id)
        self.assertStatusNotUpdated(lp3.id)
