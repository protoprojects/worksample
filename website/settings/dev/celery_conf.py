from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'set_ready_to_sync_with_encompass_loan_profiles':  {
        'task': 'advisor_portal.tasks.set_ready_to_sync_with_encompass_loan_profiles',
        'schedule': crontab(minute='0', hour='20')  # every day at 20:00
    },
    'sync_all_loan_profiles_with_encompass': {
        'task': 'advisor_portal.tasks.sync_all_loan_profiles_with_encompass',
        'schedule': crontab()  # every minute
    },
    'find_stale_in_progress_loan_profiles': {
        'task': 'advisor_portal.tasks.find_stale_in_progress_loan_profiles',
        'schedule': crontab(minute='*/5')  # every 5 minutes
    },
    'run_all_aus_requests': {
        'task': 'mismo_aus.tasks.run_all_aus_requests',
        'schedule': crontab()  # every minute
    },
    'sync_unprocessed_box_events': {
        'task': 'box.tasks.SyncUnprocessedBoxEvents',
        'schedule': crontab()  # every minutes
    },
    'handle_unprocessed_uploaded_documents': {
        'task': 'storage.tasks.HandleUnprocessedUploadedDocumentsTask',
        'schedule': crontab()  # every minutes
    },
}

# Celery testing XXXkayhudson
CELERYD_TASK_TIME_LIMIT = 300
CELERYD_MAX_TASKS_PER_CHILD = 12
