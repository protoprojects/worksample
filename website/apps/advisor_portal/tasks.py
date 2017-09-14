import datetime
import logging

from django.db import transaction
from django.utils.timezone import now

from celery import group
from celery.task import task

import box.api_v1 as api
from storage.tasks import send_document_to_encompass
from storage.models import Storage
from core.models import EncompassSync
from loans.models import LoanProfileV1


logger = logging.getLogger('sample.advisor_portal.tasks')


def _get_loan_profile_with_lock(loan_profile_id):
    loan_profile = None
    try:
        loan_profile = LoanProfileV1.objects.select_for_update().get(id=loan_profile_id)
    except LoanProfileV1.DoesNotExist:
        logger.warning('ENCOMPASS-SYNC-LOAN-PROFILE-NOT-FOUND %s', loan_profile_id)
    return loan_profile


@task
#pylint disable=C0103
def sync_loan_profile_with_encompass(loan_profile_id):
    """
    Celery task to sync the loan profile from sample to Encompass.

    :param loan_profile_id: the GUID of the loan profile
    """
    # Need to select object for update to prevent modifications
    # in the time of encompass synchronization.
    with transaction.atomic():
        logger.info('ENCOMPASS-SYNC-BEGIN-LOAN-PROFILE LoanProfleV1 object with id %s',
                    loan_profile_id)
        loan_profile = _get_loan_profile_with_lock(loan_profile_id)
        if not loan_profile:
            logger.info('ENCOMPASS-SYNC-BEGIN No LoanProfleV1 object found with id %s',
                        loan_profile_id)
            return
        logger.info('ENCOMPASS-SYNC-SET-IN-PROGRESS-FLAG guid %s', loan_profile.guid)
        loan_profile.encompass_sync_status = LoanProfileV1.ENCOMPASS_SYNC_IN_PROGRESS
        loan_profile.datetime_sent_to_encompass = now()
        loan_profile.save(
            update_fields=['encompass_sync_status', 'datetime_sent_to_encompass']
        )

    # Now need to select object again because lock is no longer exists.
    # FIXME: It is possible that some other process may change something
    #        before loan profile will selected FOR UPDATE again.
    #        Maybe we should use PostgreSQL's advisory locks.
    with transaction.atomic():
        loan_profile = _get_loan_profile_with_lock(loan_profile_id)
        if not loan_profile:
            return

        exception = None
        try:
            los_guid = loan_profile.los_sync()
            # This is an unlikely (impossible?) scenario in which loan_profile.los_sync()
            # returns successfully (no exception), but also does not include a los_guid
            # from Encompass. This is still effectively a failure case that we need to handle
            if not los_guid:
                raise ValueError('No LOS GUID was assigned by Encompass')
        except Exception as e:
            exception = e
            loan_profile.encompass_sync_status = LoanProfileV1.ENCOMPASS_SYNC_FAILED
            logger.exception('ENCOMPASS-SYNC-FAILED guid %s', loan_profile.guid)
        else:
            loan_profile.encompass_sync_status = LoanProfileV1.ENCOMPASS_SYNCED
            loan_profile.datetime_synced_with_encompass = now()
            logger.info('ENCOMPASS-SYNC-SUCCESSFUL guid %s', loan_profile.guid)
        finally:
            loan_profile.save(update_fields=['encompass_sync_status',
                                             'datetime_synced_with_encompass'])

    # Need to re-raise the exception outside of the `with transaction.atomic()`
    # otherwise, we override setting the status to FAILED on errors.
    if exception:
        # pylint: disable=raising-bad-type
        raise exception

    if loan_profile.is_encompass_synced and loan_profile.storage:
        query_params = {
            'role': api.CUSTOMER_DOCUMENTS_STORAGE_ROLE,
            'box_parent_folder_id': loan_profile.storage.storage_id
        }
        customer_storage = Storage.objects.filter(**query_params)

        if not customer_storage.exists():
            logger.info('ENCOMPASS-SYNC-DOCUMENTS Storage doesn\'t exists with params %s',
                        query_params)
            return None

        try:
            for document in customer_storage.first().documents.active().receipt():
                send_document_to_encompass.delay(document.id)
        except Exception:
            logger.exception('ENCOMPASS-SYNC-DOCUMENTS failed with unexpected error')
            raise


@task
#pylint disable=C0103
def sync_all_loan_profiles_with_encompass():
    """
    Iterate through all loan profiles that have not been synced
    and sync them with Encompass.
    """
    # check to see if encompass sync is enabled
    if not EncompassSync.enabled():
        logger.info('ENCOMPASS-SYNC-SKIPPED-NOT-ENABLED')
        return

    tasks = []
    # Selecting loan profiles ids which we need to sync with
    # encompass. We're getting ids instead of objects
    # to pass id to the subtask. Passing django object
    # as argument may cause unexpected bugs.
    loan_profiles_ids = LoanProfileV1.objects.filter(
        encompass_sync_status__in=[
            LoanProfileV1.ENCOMPASS_READY_TO_SYNC,
        ]
    ).values_list('id', flat=True)
    for lp_id in loan_profiles_ids:
        tasks.append(sync_loan_profile_with_encompass.s(lp_id))
    job = group(*tasks)
    job.apply_async()


@task
#pylint disable=C0103
def find_stale_in_progress_loan_profiles():
    """
    Need to select all loan profiles with "in progress" status which are stale for
    5 minutes to update their status.
    """
    datetime_now = now()
    loan_profiles = LoanProfileV1.objects.filter(
        encompass_sync_status=LoanProfileV1.ENCOMPASS_SYNC_IN_PROGRESS,
        datetime_sent_to_encompass__lte=datetime_now - datetime.timedelta(minutes=5)
    )
    if loan_profiles:
        logger.info('ENCOMPASS-SYNC-STALE-LOAN-PROFILES %s',
                    loan_profiles.values_list('id', flat=True))
        loan_profiles.update(encompass_sync_status=LoanProfileV1.ENCOMPASS_READY_TO_SYNC)


@task
#pylint disable=C0103
def set_ready_to_sync_with_encompass_loan_profiles():
    """
    Select for update RESPA triggered Loan Profiles.
    Prepare them for syncing with Encompass.
    """
    logger.info('SET-READY-TO-SYNC-WITH-ENCOMPASS-LOAN-PROFILES is started.')
    for loan_profile in LoanProfileV1.objects.filter(
            _respa_triggered=True,
            encompass_sync_status=LoanProfileV1.ENCOMPASS_NEVER_SYNCED):

        can_sync = loan_profile.sync_to_encompass()
        if can_sync:
            logger.info('SET-READY-TO-SYNC-FLAG guid %s', loan_profile.guid)
        else:
            reason = loan_profile.encompass_sync_warnings()
            logger.warning('READY-TO-SYNC-FLAG was not set, guid %s, reason %s',
                           loan_profile.guid,
                           reason)

    logger.info('SET-READY-TO-SYNC-WITH-ENCOMPASS-LOAN-PROFILES is finished.')
