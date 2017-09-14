from __future__ import unicode_literals

import logging
from time import gmtime, strftime
from urllib import urlencode
import requests

from boxsdk.exception import BoxAPIException
from boxsdk.object.collaboration import CollaborationRole

from django.utils.encoding import force_text

from box.utils import box_client_factory
from core.utils import is_sample_email
from core.exceptions import ServiceInternalErrorException, ServiceUnavailableException
from core.utils import send_exception_notification, format_logger_args, service_unavailable_notification


logger = logging.getLogger('sample.box.api')

FOLDER_ITEMS_LIMIT = 1000

ADVISOR_LOAN_STORAGE_ROLE = 'advisor_loan_storage'
AUS_STORAGE_ROLE = 'aus_storage'
PREQUAL_LETTER_STORAGE_ROLE = 'prequal_letter_storage'
CUSTOMER_LOAN_STORAGE_ROLE = 'customer_loan_storage'
LOANS_BASE_STORAGE_ROLE = 'loans_base_storage'

CUSTOMER_LOAN_STORAGE_TEMPLATE_ROLE = 'customer_loan_storage_template'
CUSTOMER_DOCUMENTS_STORAGE_ROLE = 'customer_loan_documents_storage'

VERSION = 'v1'

# Roles and folders specified in sample/README.txt under Bootstrapping:Box
CREDIT_REPORT_XML = 'credit_report_xml'
CREDIT_REPORT_PDF = 'credit_report_pdf'
CREDIT_REPORT_CONSUMER_PDF = 'consumer_pdf'

ADVISOR_ACL = CollaborationRole.CO_OWNER
SPECIALIST_ACL = CollaborationRole.CO_OWNER
COORDINATOR_ACL = CollaborationRole.EDITOR
CUSTOMER_ACL = CollaborationRole.VIEWER_UPLOADER

ADVISOR_LOAN_FOLDER_FORMAT = u'Client Files - {}'
ADVISOR_LOAN_SUBFOLDERS = {'adverse': '1. Adverse',
                           'funded': '2. Funded'}

# Documents uploaded by the Consumer, or shared from the Advisor to the Consumer
CUSTOMER_EXTERNAL_FOLDER_FORMAT = u'sample for {}'

# Consumer Credit Reports are stored - both source MISMO XML and a human-readable PDF
# (extracted from a binary payload in the XML)
SUBMISSION = 'submission'

CUSTOMER_INTERNAL_SUBFOLDERS_FORMATS = {'appraisal': u'{} Appraisal - [Internal]',
                                        'closing': u'{} Closing Doc - [Internal]',
                                        'conditions': u'{} Conditions - [Internal]',
                                        'disclosures': u'{} Disclosures - [Internal]',
                                        'lender': u'{} Lender - [Internal]',
                                        'private': u'{} Private - [Internal]',
                                        'AUS': u'{} AUS - [Internal]',
                                        SUBMISSION: u'{} Submission - [Internal]',
                                        'archive': u'{} Archive - [Internal]'}

CREDIT_REPORT_NAMES = {'xml': u'Full_XML_Credit_Report.xml',
                       'pdf': u'Full_PDF_Credit_Report.pdf',
                       'consumer': u'Credit_Scores.pdf'}


def box_exception_handler(custom_log=None):
    """
    Decorator for base functions box sdk.

    :param custom_log: Set if need custom logging args

    Raises:
        BoxServiceUnavailableException: Raise if box response
            http code 503, 429 or problem with network
        ServiceInternalErrorException: Raise if box response
            error http code (exclude 503, 429) or raise other exceptions.
    """

    def wrapper(func):
        def inner(*args, **kwargs):
            suffix_logger_name = func.func_name.replace('_', '-').upper()
            try:
                return func(*args, **kwargs)
            except BoxAPIException as exc:
                logger.error(
                    'BOX-SDK-API-%s %s reason %s',
                    suffix_logger_name,
                    format_logger_args(func, args, kwargs, custom_log),
                    exc
                )
                # If service unavailable or request rate limit exceeded
                if exc.status in [503, 429]:
                    raise ServiceUnavailableException()
                else:
                    raise ServiceInternalErrorException(parent_exc=exc)

            # If error in network or request
            except requests.exceptions.RequestException as exc:
                logger.error(
                    'BOX-SDK-REQUEST-%s %s reason %s',
                    suffix_logger_name,
                    format_logger_args(func, args, kwargs), exc
                )
                raise ServiceUnavailableException()

        return inner
    return wrapper


@box_exception_handler('file {box_file.object_id} folder {box_folder.object_id}')
def box_file_move(box_file, box_folder):
    """
    Move the box file to the given box folder.

    :param box_file: Box file object
    :param box_folder: Box folder object, where the item will be moved to
    :return: The updated object. Return a new box file object

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_file.move(box_folder)


@box_exception_handler('box_file {box_file.object_id} new_name {new_name}')
def box_file_rename(box_file, new_name):
    """
    Rename the box file to a new name.

    :param box_file: Box file object
    :param new_name: The new name, you want the box file to be renamed to
    :return: The updated object. Return a new box file object

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_file.rename(new_name)


@box_exception_handler('box_folder {box_folder.object_id} file_path {file_path}')
def box_file_upload(box_folder, file_path, file_name):
    """
    Upload a file to the box folder.
    The contents are taken from the given file path.

    :param box_folder: Box file object
    :param file_path: The file path of the file to upload to box folder
    :param file_name: The name to give the file on Box. If None, then use the leaf name of file_path
    :return: The newly uploaded box file object.

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_folder.upload(file_path, file_name)


@box_exception_handler('box_file {box_file.object_id} file_path {file_path}')
def box_file_update_contents(box_file, file_path):
    """
    Upload a new version of a file. The contents are taken from the given file path.

    :param box_file: Box file object
    :param file_path: The path of the file that should be uploaded
    :return: The updated object. Return a new box file object

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_file.update_contents(file_path)


@box_exception_handler('box_file {object_id}')
def box_file_get(object_id):
    """
    Initialize a box file object, whose box id is object_id.

    :param object_id: The box id of the box file object
    :return: New box file object with the given object_id.

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    box_client = box_client_factory()
    return box_client.file(object_id)


@box_exception_handler('box_file {object_id}')
def box_file_get_info(object_id):
    box_client = box_client_factory()
    return box_client.file(object_id).get()


@box_exception_handler('box_folder {box_folder.object_id} data {data}')
def box_file_update_info(box_file, data):
    """
    Edit an existing file on Box.

    :param box_file: Box file object
    :param data: The updated information about this box file object. Must be JSON serializable
    :return: The updated object. Return a new box file object

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_file.update_info(data=data)


@box_exception_handler('box_folder {box_folder.object_id} parent_folder {parent_folder.object_id}')
def box_folder_copy(box_folder, parent_folder):
    """
    Copy the box folder to the given folder.

    :param box_folder: Box folder object. Box folder to be copy
    :param parent_folder: The folder to which the box folder should be copied
    :return: Return a new copied box folder object

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_folder.copy(parent_folder)


@box_exception_handler('box_folder {box_folder.object_id} new_name {new_name}')
def box_folder_rename(box_folder, new_name):
    """
    Rename the box folder to a new name.

    :param box_folder: Box folder object
    :param new_name: The new name, you want the box folder to be renamed to
    :return: The updated object. Return a new box folder object

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_folder.rename(new_name)


@box_exception_handler('box_folder {box_folder.object_id} file_name {file_name}')
def box_file_upload_stream(box_folder, file_stream, file_name):
    """
    Upload a file to the box folder.
    The contents are taken from the given file stream, and it will have the given name.

    :param box_folder: Box folder object
    :param file_stream: The file-like object containing the bytes
    :param file_name: The name to give the file on Box.
    :return: The newly uploaded box file object.

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    return box_folder.upload_stream(file_stream=file_stream, file_name=file_name)


@box_exception_handler()
def box_folder_save(parent, name, acls, may_exist=False, description=None):
    """
    Create or update box folder.

    :param parent: Box folder object
    :param name: Folder name
    :param acls: List collaborators with email and role to give access
    :param may_exist: If True and raise except, trying get folder. Defaults to False
    :param description: Description box folder. Defaults to None
    :return: New or updated Box folder object

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code

    Note: If this transaction fails initially and is retried, make sure to pass may_exist=True
    """
    logger.debug('FOLDER-SAVE parent %s name %s', parent.object_id, name)
    try:
        box_folder = parent.create_subfolder(name)
        logger.debug('FOLDER-CREATED parent %s name %s', parent.object_id, name)
    except BoxAPIException as exc:
        # If folder exists get it
        if may_exist and (exc.code == 'item_name_in_use'):
            box_folder = box_subfolder_get(parent, name)
        else:
            raise

    if description is not None:
        try:
            box_folder.update_info(data={'description': str(description)})
        except BoxAPIException as exc:
            logger.error(
                'FOLDER-UPDATE-DESCRIPTION folder %s description %s exc %s',
                box_folder.object_id, description, exc
            )
            raise

    if box_folder and acls:
        box_folder_acls_set(box_folder, acls)
    return box_folder


@box_exception_handler()
def base_storage_get(role):
    """
    Get first Storage object with a given role.

    :param role: Name role storage
    :return: Storage object on success; None on storage with given role not found
    """
    # Cyclic import. This file imported in models.py app storage
    from storage.models import Storage
    base_storage = Storage.objects.filter(role=role, version=VERSION).first()
    if base_storage is None:
        logger.warning('BASE-STORAGE-NOT-FOUND role %s', role)
    return base_storage


@box_exception_handler()
def box_folder_get(storage):
    """
    Get box folder object out of Storage object.

    :param storage: Storage object
    :return: box folder on success; None on not found storage

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    if not storage:
        logger.debug('NO-STORAGE')
        return None
    if not storage.storage_id:
        logger.debug('NO-STORAGE-ID storage %s', storage.id)
        return None
    box_client = box_client_factory()

    try:
        folder = box_client.folder(storage.storage_id)
    except BoxAPIException as exc:
        logger.error('NO-FOLDER-ID folder %s exc %s', storage.storage_id, exc)
        raise
    return folder


@box_exception_handler()
def advisor_loan_folder_create(parent_folder, advisor):
    """
    Create an advisor folder structure.

    :param parent_folder: Box folder object
    :param advisor: Advisor model object
    :return: New or updated Box parent folder object
    """
    folder_name = ADVISOR_LOAN_FOLDER_FORMAT.format(advisor.username)
    acls = [(force_text(advisor.email), ADVISOR_ACL)]
    folder = box_folder_save(parent_folder, folder_name, acls)
    for folder_name in ADVISOR_LOAN_SUBFOLDERS.values():
        box_folder_save(folder, folder_name, acls=None, may_exist=True)
    return folder


@box_exception_handler()
def advisor_loan_storage_update(advisor):
    """
    Retrieve/create the loan storage for an advisor.

    :param advisor: Advisor model object
    :return: The storage model object on success; None on error/inactive advisor.
    """
    if not advisor.is_active:
        return None

    advisor_storage = None
    if advisor.storages:
        advisor_storage = advisor.storages.filter(
            role=ADVISOR_LOAN_STORAGE_ROLE, version=VERSION).first()

    if advisor_storage is None:
        logger.debug('ADVISOR-LOAN-STORAGE-NOT-FOUND %s', advisor.username)
        base_storage = base_storage_get(role=LOANS_BASE_STORAGE_ROLE)

        if not base_storage:
            return None

        parent = box_folder_get(base_storage)
        advisor_folder = advisor_loan_folder_create(parent, advisor)
        advisor_storage = advisor.storages.create(
            name='{} Loans'.format(advisor.username),
            storage_id=advisor_folder.id,
            role=ADVISOR_LOAN_STORAGE_ROLE,
            is_active=True,
            user=advisor,
            version=VERSION)
        logger.info('ADVISOR-LOAN-STORAGE-CREATED %s', advisor.username)
    return advisor_storage


def _borrower_folder_name_get(borrower, uniquifier):
    """
    Generate the name of the top-level borrower folder

    :param borrower: the borrower object
    :param uniquifier: from the loan_profile/application
    :return: String with borrower folder name
    """
    first_name = borrower.first_name
    last_name = borrower.last_name
    if last_name and first_name:
        fmt = '{last_name}, {first_name} {uniq}'
    elif not last_name and first_name:
        fmt = '{first_name} {uniq}'
    elif last_name and not first_name:
        fmt = '{last_name}, {uniq}'
    else:
        fmt = '{uniq}'
    return fmt.format(last_name=last_name, first_name=first_name, uniq=uniquifier)


def customer_loan_internal_folders_create(folder_name_base, parent_folder):
    """
    Create internal load folders for customer.

    :param folder_name_base: Base folder name. Use from generation full folder name
    :param parent_folder: Box folder object in which you want to create an subfolders
    :return: None
    """
    acls = []
    for key, folder_fmt in CUSTOMER_INTERNAL_SUBFOLDERS_FORMATS.items():
        folder_name = folder_fmt.format(folder_name_base)
        box_folder = box_folder_save(parent_folder, folder_name, acls)
        if key == SUBMISSION:
            # Cyclic import. This file imported in models.py app storage
            from storage.models import Storage
            storage = Storage.objects.create_submission_storage(box_folder)


@service_unavailable_notification(service_name='Box', custom_log='{loan_profile.guid}')
def get_or_create_loan_profile_box_folder(loan_profile, external_template):
    """
    Create/retrieve LoanProfile box folder id
    The storage is associated with the first borrower of the loan profile.

    :param loan_profile: Loan profile model object
    :param external_template: Storage model object
    :return: Customer box folder id on success; None on inactive loan_profile or
        failed to get advisor loan storage
    """
    prefix = 'LOAN-PROFILE-STORAGE-UPDATE'
    logger.debug('%s %s', prefix, loan_profile.guid)

    customer = loan_profile.borrowers.first()
    if not customer:
        logger.info('%s-UPDATE-NO-BORROWER %s', prefix, loan_profile.guid)
        return None

    if customer.username.strip() == '':
        logger.info('%s-BORROWER-NO-NAME %s bor %s', prefix, loan_profile.guid, customer.id)
        return None

    advisor = loan_profile.advisor
    if not advisor:
        logger.warning('%s-NO-ADVISOR %s', prefix, loan_profile.guid)
        return None

    logger.debug('%s-CREATE %s borrower %s', prefix, loan_profile.guid, customer.username)
    ma_storage = advisor.storages.filter(role=ADVISOR_LOAN_STORAGE_ROLE, is_active=True).first()
    if not ma_storage:
        logger.warning('%s-ADVISOR-STORAGE-NOT-FOUND %s advisor %s', prefix, loan_profile.guid, advisor.username)
        return None

    ma_folder = box_folder_get(ma_storage)
    folder_name_base = _borrower_folder_name_get(customer, loan_profile.uniquifier)
    customer_folder = box_subfolder_get(ma_folder, folder_name_base)
    if not customer_folder:
        acls = []
        customer_folder = box_folder_save(ma_folder, folder_name_base, acls, description=loan_profile.guid)
        customer_loan_internal_folders_create(folder_name_base, customer_folder)
        customer_loan_external_folders_create(
            customer, customer_folder, folder_name_base, external_template
        )
    return customer_folder.id


@box_exception_handler()
def box_folder_acls_set(folder, acls):
    """
    Set collaborators to box folder.

    :param folder: Box folder object
    :param acls: List collaborators with email and role to give access
    :return: None

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    for email, role in acls:
        try:
            folder.add_collaborator(email, role, True if is_sample_email(email) else False)
        except BoxAPIException as exc:
            email = email if is_sample_email(email) else 'email_blocked_since_not_sample_email'
            if getattr(exc, 'code', None) != 'user_already_collaborator':
                logger.error('FOLDER-ACL-SET-EXCEPTION %s email %s exc %s', folder.object_id, email, exc)
                raise


@service_unavailable_notification(service_name='Box', custom_log='{loan_profile.guid}')
def loan_profile_folder_add_advisor(loan_profile, advisor):
    """
    Add access advisor on loan profile box folder.

    :param loan_profile: Loan profile model object
    :param advisor: Advisor model object
    :return: True on success; False if loan profile folder not found
    """
    slug_prefix = 'ADD-ADVISOR-TO-LOAN-PROFILE-FOLDER'
    logger.debug('%s-INITIATE advisor %s lp %s', slug_prefix, advisor, loan_profile.guid)

    lp_folder = box_folder_get(loan_profile.storage)
    if not lp_folder:
        return False

    acls = [(force_text(advisor.email), ADVISOR_ACL)]
    box_folder_acls_set(lp_folder, acls)

    logger.debug('%s-COMPLETE advisor %s lp %s', slug_prefix, advisor, loan_profile.guid)
    return True


@box_exception_handler()
def box_subfolder_get(parent_folder, subfolder_name, should_exist=False):
    """
    Get box subfolder.

    :param parent_folder: Box folder object
    :param subfolder_name: Name subfolder
    :param should_exist: If True add warning logging. Defaults to False
    :return: Box folder on success; None if subfolder not found in parent folder
    """
    try:
        folder_items = parent_folder.get_items(FOLDER_ITEMS_LIMIT)
    except BoxAPIException as exc:
        logger.error('SUBFOLDERS-LIST folder %s exc %s', parent_folder.object_id, exc)
        raise

    for entry in folder_items:
        if entry.name == subfolder_name:
            break
    else:
        if should_exist:
            logger.warning(
                'SUBFOLDER-NOT-FOUND parent %s subfolder_name %s',
                parent_folder.object_id, subfolder_name
            )
        entry = None
    return entry


def customer_loan_external_folders_create(customer, parent_folder, folder_name_base, external_template):
    """
    Create customer loan external folder.

    :param customer: Customer model object
    :param parent_folder: Customer box folder
    :param folder_name_base: Base folder name. Use from generation full folder name
    :param external_template: External box folder template
    :return: None
    """
    # Cyclic import. This file imported in models.py app storage
    from storage.models import Storage
    prefix = 'CUSTOMER-LOAN-EXTERNAL-FOLDERS'
    external_folder_name = CUSTOMER_EXTERNAL_FOLDER_FORMAT.format(folder_name_base)

    if box_subfolder_get(parent_folder, external_folder_name):
        logger.debug('%s-EXIST %s', prefix, customer.username)
        return None

    if not external_template:
        logger.warning(
            '%s-NO-TEMPLATE-FOR-ROLE role %s',
            prefix, CUSTOMER_LOAN_STORAGE_TEMPLATE_ROLE
        )
        return None

    template_folder = box_folder_get(external_template)

    customer_external_folder = box_folder_copy(template_folder, parent_folder)
    box_folder_rename(customer_external_folder, external_folder_name)
    if customer.email:
        customer_acl = [(customer.email, CUSTOMER_ACL)]
        box_folder_acls_set(customer_external_folder, customer_acl)
    else:
        logger.warning('%s-NOT-SHARED %s', prefix, folder_name_base)
    logger.debug('%s-CREATED %s', prefix, folder_name_base)
    Storage.objects.create_documents_storage(
        customer_external_folder, parent_folder, external_folder_name
    )


def get_customer_loan_external_folder(loan_profile):
    """
    Get customer loan external box folder.

    :param loan_profile: LoanProfile model object
    :return: Box folder object on success; None on box sdk error or failed to get customer_folder

    Note: Eating exception BoxAPIException
    """
    customer = loan_profile.borrowers.first()

    if not loan_profile.advisor:
        return None

    advisor = loan_profile.advisor
    if advisor.storages.count() == 0:
        return None

    ma_storage = advisor.storages.filter(
        role=ADVISOR_LOAN_STORAGE_ROLE, is_active=True).first()

    ma_folder = box_folder_get(ma_storage)
    folder_base = _borrower_folder_name_get(customer, loan_profile.uniquifier)
    customer_folder = box_subfolder_get(ma_folder, folder_base)

    if not customer_folder:
        return None

    external_folder_name = CUSTOMER_EXTERNAL_FOLDER_FORMAT.format(folder_base)
    try:
        subfolder = box_subfolder_get(customer_folder, external_folder_name)
    # TODO Need review. Asana #287939142987750
    except BoxAPIException as exc:
        logger.error('BOX-FILE-GET-EXTERNAL-FOLDER loan_profile %s exc %s', loan_profile.guid, exc)
        subfolder = None
    return subfolder


@box_exception_handler()
def _extract_existing_folder_base(loan_profile_folder):
    """
    The loan_profile_folder's name is the folder base name.

    :param loan_profile_folder: Box folder object
    :return: Name box Folder

    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    try:
        lp_info = loan_profile_folder.get()
    except BoxAPIException as exc:
        logger.error('BOX-GET-FOLDER folder %s exc %s', loan_profile_folder.object_id, exc)
        raise
    return lp_info['name']


def get_loan_profile_subfolder(loan_profile, subfolder_name):
    """
    Given a loan_profile and a subfolder_name, return that loan_profile's subfolder as a Box Folder object.

    :param loan_profile: The loan profile object
    :param subfolder_name: The name of the subfolder (a key in CUSTOMER_INTERNAL_SUBFOLDERS_FORMATS)
    :return: Box folder object on success. None if subfolder not in box loan profile folder
    """
    lp_folder = box_folder_get(loan_profile.storage)
    lp_base_name = _extract_existing_folder_base(lp_folder)
    subfolder_name = CUSTOMER_INTERNAL_SUBFOLDERS_FORMATS[subfolder_name].format(lp_base_name)
    return box_subfolder_get(lp_folder, subfolder_name)


def _get_loan_profile_external_subfolder(loan_profile):
    """
    Get loan profile customer's external sub-folder. (sample for ...)

    :param loan_profile: Loan profile model object
    :return: Box folder on success; None if not find box folder
    """
    lp_folder = box_folder_get(loan_profile.storage)
    lp_base_name = _extract_existing_folder_base(lp_folder)
    external_folder = box_subfolder_get(
        lp_folder, CUSTOMER_EXTERNAL_FOLDER_FORMAT.format(lp_base_name))
    return external_folder


@service_unavailable_notification(service_name='Box', custom_log='{loan_profile.guid}')
def store_credit_report(loan_profile, credit_report_file_stream, file_type='xml'):
    """
    Upload the given xml file to the Sumissions Internal Folder

    :param loan_profile: Loan profile model object
    :param credit_report_file_stream: The file-like object containing the bytes
    :param file_type: File type of credit report.
    :return: Box File object on success; None if box api response 4xx or 5xx http code
    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    file_name = CREDIT_REPORT_NAMES[file_type]

    try:
        xml_dest_folder = get_loan_profile_subfolder(loan_profile, SUBMISSION)
        return box_file_upload_stream(
            xml_dest_folder,
            file_stream=credit_report_file_stream,
            file_name=file_name)
    except BoxAPIException as exc:
        logger.error(
            'BOX-FILE-SAVE-CREDIT-REPORT-%s-EXCEPTION loan_profile %s exc %s',
            file_type.upper(), loan_profile.guid, exc
        )
        raise


@service_unavailable_notification(service_name='Box', custom_log='{loan_profile.guid}')
def store_consumer_pdf(loan_profile, pdf_file_stream):
    """
    Upload the given xml file to the customer's external sub-folder. (sample for ...)

    :param loan_profile: Loan profile model object
    :param pdf_file_stream: The file-like object containing the bytes
    :return: Box File object
    :raises BoxAPIException: Raise if box api response 4xx or 5xx http code
    """
    try:
        pdf_dest_folder = _get_loan_profile_external_subfolder(loan_profile)
        return box_file_upload_stream(
            pdf_dest_folder,
            file_stream=pdf_file_stream,
            file_name=CREDIT_REPORT_NAMES['consumer']
        )
    except BoxAPIException as exc:
        logger.error(
            'BOX-FILE-SAVE-CREDIT-CONSUMER-PDF-EXCEPTION loan_profile %s exc %s',
            loan_profile.guid, exc
        )
        raise


def _get_new_archive_name(filename):
    """
    Create a common format for credit report files that have to be renamed
    to allow a retry.

    :param filename: String file name
    :return: String archive file name
    """
    prefix = strftime("Old File Archived at %Y-%m-%d %H:%M", gmtime())
    return "{} ({})".format(prefix, filename)


#TODO: Remove in ENG-55
def archive_credit_report_storage(credit_storage):
    """
    Rename the credit folder to allow for a retry

    :param credit_storage: Storage model object
    :return: True if renamed credit report folder Documents. False if box api response 4xx or 5xx http code

    Note: Eating exception BoxAPIException
    """
    try:
        credit_folder = box_folder_get(credit_storage)
        try:
            folder_items = credit_folder.get_items(FOLDER_ITEMS_LIMIT)
        except BoxAPIException as exc:
            logger.error('BOX-ARCHIVE-CREDIT-REPORT-STORAGE failed to retrieve folder items from %s exc %s',
                credit_folder.object_id, exc)
            raise

        for entry in folder_items:
            logger.warning('entry %s', entry)
            if entry.name == CREDIT_REPORT_NAMES['xml'] or entry.name == CREDIT_REPORT_NAMES['pdf']:
                box_file_rename(entry, _get_new_archive_name(entry.name))
        return True
    # TODO Need review. Asana #287939142987750
    except BoxAPIException as exc:
        lp = credit_storage.get_loan_profile()
        lp_guid = getattr(lp, 'guid', None)
        send_exception_notification(lp_guid, 'Box', str(exc))
        logger.exception(
            'BOX-FILE-ARCHIVE-CREDIT-REPORT-XML-EXCEPTION storage_id %s exc %s',
            credit_storage.storage_id, exc
        )
        return False


def archive_credit_report_file(credit_report_document):
    """
    Rename the credit file to allow for a retry

    :param credit_report_document: Document model object
    :return: True if renamed credit report file. False if box api response 4xx or 5xx http code

    Note: Eating exception BoxAPIException
    """
    try:
        credit_file = box_file_get(credit_report_document.document_id)
        credit_file_name = credit_file.get()['name']
        box_file_rename(credit_file, _get_new_archive_name(credit_file_name))
        return True
    # TODO Need review. Asana #287939142987750
    except BoxAPIException as exc:
        lp = credit_report_document.get_loan_profile()
        lp_guid = getattr(lp, 'guid', None)
        send_exception_notification(lp_guid, 'Box', str(exc))
        logger.exception(
            'BOX-FILE-ARCHIVE-CREDIT-REPORT-XML-EXCEPTION storage_id %s exc %s',
            credit_report_document.storage_id, exc
        )
        return False


def get_storage_object_url(storage_obj):
    """
    Given a storage object, return the url accessing it.

    :param storage_obj: Storage model object
    :return: String url for access to box file on success;
        Empty string on problem with box api or box file not found

    Note: Eating exception BoxAPIException
    """
    storage_url = ""
    try:
        storage_file = box_file_get(storage_obj.storage_id)
        storage_url = storage_file.get_url()
    # TODO Need review. Asana #287939142987750
    except BoxAPIException as exc:
        logger.error('BOX-FILE-GET-URL-EXCEPTION storage_id %s exc %s', storage_obj.storage_id, exc)
    return storage_url


@service_unavailable_notification(service_name='Box', custom_log='{loan_profile.guid}')
def store_aus(report_name, loan_profile, file_stream):
    """
    Stores all reports from AUS response, returns Box File object.

    :param report_name: File name report
    :param loan_profile: Loan profile model object
    :param file_stream: The file-like object containing the bytes
    :return: Box file object uploaded file on success;
        None if box api response 4xx or 5xx http code

    Note: Eating exception BoxAPIException
    """
    try:
        aus_folder = get_loan_profile_subfolder(loan_profile, 'AUS')
        return box_file_upload_stream(
            aus_folder, file_stream=file_stream, file_name=report_name
        )
    # TODO Need review. Asana #287939142987750
    except BoxAPIException as exc:
        logger.error(
            'BOX-FILE-SAVE-AUS-FILE-EXCEPTION loan_profile %s file %s exc %s',
            loan_profile.guid, report_name, exc
        )
        return None


def get_thumbnail(document_obj):
    """
    Get thumbnail box file

    :param document_obj: Document model object
    :return: Content thumbnail ob success; None if box api response 4xx or 5xx http code

    Note: Eating exceptions like BoxAPIException and requests.exceptions.RequestException
    """
    box_client = box_client_factory()
    box_file = box_file_get(document_obj.document_id)  # box file instance
    params = {'max_height': 160, 'max_width': 160,
              'min_height': 80, 'min_width': 80}
    url = box_file.get_url('thumbnail.jpg') + '?' + urlencode(params)
    try:
        response = box_client.make_request('GET', url, expect_json_response=False, stream=True)
    except (BoxAPIException, requests.exceptions.RequestException) as exc:
        # eating exceptions to avoid downstream failures
        logger.exception('BOX-GET-THUMBNAIL-EXCEPTION %s, exc: %s', document_obj.__repr__(), exc)
        return None
    return response.content
