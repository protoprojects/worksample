# Debugging post-commit in django 1.8

## Description
After registration, we have an issue where the celery task that's intended to load the new record created by the registration finds that the request hasn't committed the matching record for the ID to the database yet. This application is using `ATOMIC_REQUESTS`, and a local celery instance. The primary issue appears to be the lack of a synchronous save call to chain the celery task execution to.

We don't want to send the entire object as the celery payload, as it may contain sensitive information (we'd have to secure the celery backing store.) Django 1.9 appears to have an `on_commit` hook that would help us resolve this in a number of contexts

We're currently working around this by using the "delay" parameter for the job to include a 20s lag:

```python
push_loan_profile_to_salesforce.apply_async(args=[self.loan_profile.id], countdown=20)
```

but this is extremely fragile.

## Core Code:

`customer_portal/serializers/loan_profile_v1.py`:

```python
    def create(self, validated_data):
        ''' create loan_profile '''
        try:
            with transaction.atomic():
                # TODO: create storage?
                # pylint: disable=attribute-defined-outside-init
                self.loan_profile = self._create_loan_profile(
                    self.customer,  # assigned in view
                    self.mortgage_profile,  # assigned in view
                    validated_data,
                )
                if self.mortgage_profile:
                    self.loan_profile.mortgage_profiles.add(self.mortgage_profile)
                self.demographics = _create_demographics()
                self.borrower = self._create_borrower(self.customer, self.loan_profile, self.demographics)
                self.borrower_incomes = _create_incomes(self.borrower)
                self.borrower_assets = self._create_assets(self.borrower)
                self.borrower_expenses = self._create_expenses(self.borrower)
        except IntegrityError as e:
            logger.exception('CUSTOMER-CREATE-LOAN-PROFILE-EXCEPTION %s', e.message)
        else:
            push_loan_profile_to_salesforce.delay(self.loan_profile.id)
            return self.loan_profile
```

`customer_portal/views/loan_profile_v1.py`:

```python
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.mortgage_profile = get_mortgage_profile_from_current_session(request)
        serializer.customer = request.user.customer
        serializer.save()  # serializer.save() calls serializer.create()
        if serializer.mortgage_profile is None:
            logger.debug('NO-MORTGAGE-PROFILE-FOUND customer %s', serializer.customer.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)```

`vendors/tasks.py`

```python
@task
def push_loan_profile_to_salesforce(loan_profile_v1_id):
    '''loan profile -> lead'''
    sf_push = SalesforceLoanProfilePush(loan_profile_v1_id)
    sf_push.push()
```

`vendors/sf_push.py`

```python
class SalesforceLoanProfilePush(object):
    '''
    Transmit a sample LoanProfileV1 + MortgageProfile
    to salesforce as a lead for consumer portal
    '''

    def __init__(self, loan_profile_v1_id):
        try:
            loan_profile = LoanProfileV1.objects.get(id=loan_profile_v1_id)
        except ObjectDoesNotExist as exc:
            logger.error("SF-LOAN-LEAD_PUSH FAILED - LPv1 %d not found", loan_profile_v1_id)
            raise exc
        else:
            context_map = copy.deepcopy(SF_REGISTRATION_STATICS)
            if loan_profile.mortgage_profile:
                if loan_profile.mortgage_profile.id:
                    context_map['typed_profile'] = SalesforceUtils.typed_mortgage_profile(
                        loan_profile.mortgage_profile)

            self.serializer = sampleLoanProfileSerializer(loan_profile, context=context_map)
            self.loan_profile = loan_profile

    def push(self):
        '''send contact to SF'''
        loan_map = self.serializer.data

        # ALIBI: serializer conflict with reserved 'type' on object
        loan_map['type'] = 'Lead'

        salesforce_client = SalesforceUtils.create_salesforce_client()
        if salesforce_client:
            try:
                if self.loan_profile.crm_id:
                    # ALIBI: serializer conflict with reserved "id" on object
                    loan_map['Id'] = self.loan_profile.crm_id
                    response = salesforce_client.update(loan_map)
                else:
                    response = salesforce_client.create(loan_map)
            except Exception as exc:
                logger.exception('SF-LOAN-LEAD-PUSH FAILED')
                raise exc
            else:
                if isinstance(response, list) and len(response) == 1:
                    if 'success' in response[0].keys() and response[0]['success']:
                        logger.info(
                            'SF-LOAN-LEAD-PUSH %s, url: %s -> lead Id : %s',
                            self.loan_profile.guid,
                            salesforce_client.serverUrl, response[0]['id'])
                        if not self.loan_profile.crm_id:
                            self.loan_profile.crm_id = response[0]['id']
                            self.loan_profile.crm_type = SF_CONTACT_CRM_TYPE
                        self.loan_profile.crm_last_sent = datetime.utcnow().replace(tzinfo=tzutc())
                        self.loan_profile.save()
                    else:
                        logger.error('SF-LOAN-LEAD-PUSH FAILED: response[0]: %s', response[0])
                else:
                    logger.error('SF-LOAN-LEAD-PUSH FAILED: response: %s', response)

                if response and not self.loan_profile.advisor:
                    # commence transaction to get advisor for loan
                    sf_request = SalesforceAdvisorRequest(self.loan_profile.id)
                    sf_request.query()

```



## The Error

```
ERROR sample.vendors.sf_push SF-LOAN-LEAD_PUSH FAILED - LPv1 401 not found
[2016-03-24 11:40:48,493: ERROR/Worker-4] SF-LOAN-LEAD_PUSH FAILED - LPv1 401 not found
[2016-03-24 11:40:48,500: ERROR/MainProcess] Task vendors.tasks.push_loan_profile_to_salesforce[9b1766b7-56d6-483b-956b-ccf1b263734b] raised unexpected: DoesNotExist('LoanProfileV1 matching query does not exist.',)
Traceback (most recent call last):
  File "/Users/andycarra/rksh/lib/python2.7/site-packages/celery/app/trace.py", line 240, in trace_task
    R = retval = fun(*args, **kwargs)
  File "/Users/andycarra/rksh/lib/python2.7/site-packages/celery/app/trace.py", line 438, in __protected_call__
    return self.run(*args, **kwargs)
  File "/Users/andycarra/rksh/sample/website/apps/vendors/tasks.py", line 17, in push_loan_profile_to_salesforce
    sf_push = SalesforceLoanProfilePush(loan_profile_v1_id)
  File "/Users/andycarra/rksh/sample/website/apps/vendors/sf_push.py", line 103, in __init__
    raise exc
Exception: LoanProfileV1 matching query does not exist.
```            

## Approaches


### Explicit relaxation of transaction with internal transaction (implicit savepoint):

`/website/apps/customer_portal/views/loan_profile_v1.py`

```python
+    @transaction.non_atomic_requests
     def create(self, request, *args, **kwargs):
-        serializer = self.get_serializer(data=request.data)
-        serializer.is_valid(raise_exception=True)
-        serializer.mortgage_profile = get_mortgage_profile_from_current_session(request)
-        serializer.customer = request.user.customer
-        serializer.save()  # serializer.save() calls serializer.create()
-        if serializer.mortgage_profile is None:
-            logger.debug('NO-MORTGAGE-PROFILE-FOUND customer %s', serializer.customer.id)
+        loan_profile_id = None
+        try:
+            with transaction.atomic():
+                serializer = self.get_serializer(data=request.data)
+                serializer.is_valid(raise_exception=True)
+                serializer.mortgage_profile = get_mortgage_profile_from_current_session(request)
+                serializer.customer = request.user.customer
+                lp = serializer.save()  # serializer.save() calls serializer.create()
+                if serializer.mortgage_profile is None:
+                    logger.debug('NO-MORTGAGE-PROFILE-FOUND customer %s', serializer.customer.id)
+                logger.info("LPID: %d", lp.id)
+                logger.info("%s", loan_models.LoanProfileV1.objects.get(id=lp.id))
+                loan_profile_id = lp.id
+        except Exception as exc:
+                    logger.debug('LOAN-PROFILE-CREATION-FAILED %s', exc)
+        push_loan_profile_to_salesforce.delay(loan_profile_id)
         return Response(serializer.data, status=status.HTTP_201_CREATED)
```

Hoping that by embedded an explicit transaction inside a non-transactional context, we could force transactional save.

<b>FAILED (same error)</b>

### Signal for `post_save`
`website/apps/customer_portal/views/loan_profile_v1.py`

```python
+@receiver(post_save, sender=LoanProfileV1, dispatch_uid="loan_profile_created")
+def loan_profile_created(sender, instance, created, **kwargs):
+    if created:
+        push_loan_profile_to_salesforce.delay(instance.id)
```

This was the most promising, but this is an event *after save has been called*, not *after save has returned*

<b>FAILED (same error)</b>

### Explicit savepoint:
`customer_portal/serializers/loan_profile_v1.py` inside `create`:

```python
            sid = transaction.savepoint()
            try:
                with transaction.atomic():
					...
            transaction.savepoint_commit(sid)
```
This was a complete hail mary, included for completeness' sake.

<b>FAILED (same error)</b>

### Explicit internal atomicity, catch all exceptions:
`customer_portal/serializers/loan_profile_v1.py` inside `create`:

```python
    @transaction.atomic
    def create(self, validated_data):
        ...
         except IntegrityError as e:
             logger.exception('CUSTOMER-CREATE-LOAN-PROFILE-EXCEPTION %s', e.message)
         except Exception as exc:
             logger.exception('CUSTOMER-CREATE-LOAN-PROFILE-EXCEPTION-ALL %s', exc.message)
```
`website/apps/customer_portal/views/loan_profile_v1.py`

```python
+    @transaction.non_atomic_requests
     def create(self, request, *args, **kwargs):
         serializer = self.get_serializer(data=request.data)
         serializer.is_valid(raise_exception=True)
         serializer.mortgage_profile = get_mortgage_profile_from_current_session(request)
         serializer.customer = request.user.customer
-        serializer.save()  # serializer.save() calls serializer.create()
+        lp = serializer.save()  # serializer.save() calls serializer.create()
         if serializer.mortgage_profile is None:
             logger.debug('NO-MORTGAGE-PROFILE-FOUND customer %s', serializer.customer.id)
+        logger.info("LPID: %d", lp.id)
+        logger.info("%s", loan_models.LoanProfileV1.objects.get(id=lp.id))
+        push_loan_profile_to_salesforce.delay(lp.id)
         return Response(serializer.data, status=status.HTTP_201_CREATED)
```
<b>FAILED (same error, no exception thrown)</b>

