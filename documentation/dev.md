# Development Notes


## Documentation Conventions
- `CAPITALIZED-TOKENS` are used to indicate parts of the command you
should replace as needed.


## Assumptions
- You have created a fork of the `sample` repository
- You have generated an ssh keypair on your development machine
- You have updated your github settings to include that ssh keypair


## Setting Up Your Local Repository
- Clone your fork of the sample repository (substitute `USER` with your github name)
  - `git clone git@github.com:USER/sample.git sample`
- Add the `sample/sample` repository as a the `upstream` remote
  repository
  - `git remote add upstream git@github.com:sample/sample.git`
- Check your work (the output should include `origin` and `upstream`)
  - `git remote --verbose`


## Staying Up-to-Date
- Fetch remote updates
  - `git fetch --all`
- Checkout the integration branch to update (labelled below as `BRANCH`)
  - `git checkout int-BRANCH`
- Apply the recent changes. If there is a conflict, something is awry.
  - `git merge --ff-only upstream/int-BRANCH`
- Push the changes to your own repostory. If there is a conflict, something is amiss
  - `git push origin int-BRANCH`
- Incorporate the changes into your feature branch with `rebase` instead
  of `merge`.
  - `git checkout MY-LOCAL-FIX-BRANCH`
  - `git rebase -i upstream/int-BRANCH`


## Code Conventions
- Use style and convention tools on changed files.  Avoid increasing warnings and errors when commiting changes.

- Run pep8 and pylint with one command (set `int-labyrinth` to a base branch as needed)
  - `make pep lint REF_BRANCH=int-labyrinth PYLINT_REPORT=n`

- For python
  - pep8: `PYTHONPATH=website/apps pep8 --config=website/pep8.rc $(git diff --name-only upstream/int-BRANCH | egrep '\.py$')`
  - pylint: `PYTHONPATH=website/apps pylint -r n --rcfile=website/pylint.cfg $(git diff --name-only upstream/int-BRANCH | egrep '\.py$')`
- For coffeescript
  - advisor portal: `make check_js` (then consult `reports/coffeelint.xml`)
  - sample/sample: all js now deprecated - no need
- For Javascript
  - sample/consumer-portal: When you run `gulp serve`, all files are being watched and linted upon new changes.
- For CSS/SASS:
  - http://cssguidelin.es/ & http://sass-guidelin.es/


## Unit Tests
- Unit tests should run without requiring a network connection

- Use `core.utils.LogMutingTestMixinBase` as needed to reduce log
  noise. If your test case overrides `setup()` or `teardown()`, it
  will need to call `super(...,self ).setup()` or `super(...,
  self).teardown()` as well.


## Code Coverage
Coverage is a two-step process
- Generate coverage information
  - `PYTHONPATH=website/apps coverage run --source='.' manage.py test --failfast --nomigrations website.apps.encompass.tests.test_loan_synchronization`
- Run the coverage report
  - `coverage report --include='website/apps/encompass/*.py' '--omit=website/apps/*/migrations/*' --show-missing`


## Commit Messages
The current Asana-github integration is not as full-featured as one
might hope. To make it easier for product, qa, and development to find what
tasks are in a given release, the first commit message for a PR should
be in the following form

```
Asana #ASANA-TASK-ID -- Brief description
tags: 'BRANCH'
- specific change note 1
- specific change note 2
```

where
- `ASANA-TASK-ID` is the last long number in the url for the task
- `BRANCH` is the git integration branch name in lower case, e.g., `odin`

After (or during) feedback, rebase to reduce commit history to
essential commits. This also makes it easier to scanning for tasks in
a release. More information on `git rebase` may be found at

If your change is not associated with an Asana task
- create a task (preferable)
- or use `MAINT` (for release-related things) or `FIX` (for
  teeny-tiny fixes) in place of the `Asana #ASANA-TASK-ID` portion


## Pull Requests
- Create pull requests against the current integration branch

- Make sure the code passes all unit tests locally. The top-level
  `README.md` files should include more information on running unit tests.


# Code Review Notes
Code review is an important part of development. When reviewing code
remember to check for

- the base branch is correct (especially not `master` except for
  extreme circumstances)

- standalone documentation for new django apps

- documentation within the code

- sufficient unit test coverage

- properly formatted commit message

- no new lint warnings

If the PR is suitable for merging
- leave a comment to that effect, e.g., `shipit`, `lgtm`, _etc._

- wait for the checks to pass

- merge

- notify the author that the pr has been merged (via slack, e-mail, or
  one of the means outlined in https://tools.ietf.org/html/rfc1217)


# Release Notes
- Releases are each week on Tuesday

- Code freeze is at Noon, Wednesday. PRs that go up after noon go into
  the next release

- Releases follow a 1 week development + 6 day qa cycle

- The upcoming release branch is in the `qa3` environment (aka
 `on qa`). This branch is closed for development apart from bug fixes.

- The ci server automatically deploys changes to the following release branch to beta. This is the ongoing development branch.


# Asana Notes
When you begin working on a task, move it to the `Current` section for
its various projects. If you put it aside for whatever reason, please change
the section to `Backlog`.

When a PR merge completes a task, the developer of the code *must*
- verify the change on beta. The extent of verification depends on the
  change itself, e.g., loading the home page, completing a
  questionnaire with no console warnings/errors, syncing a loan and
  checking encompass, _etc_.

- change the project sections to `To Validate` or `Testing Backlog`
depending on the project

- assign the task to `Blake Ross`, digital oil painter extraordinaire

# Celery Notes
If you want  to debug celery tasks/celeryd locally, you'll need to add some config elements to your development settings, and it helps to have a few commands at your beck and call. It's important to note that you can do without running a local `celeryd` for most development tasks; you can simply add

```
CELERY_ALWAYS_EAGER = True
```
to your `dev.py` settings and celery tasks will execute synchronously... but if you have timing/asychrony-related issues, read-on.

## Settings up celery locally
These settings are now included in the `dev.txt` requirements file and the example dev settings file. If you have an old template, you make need to add the following manually.

### Requirements
You'll need to add celery to your development requirements:

```
celery-with-redis
```
and re-run the necessary `pip install` command for your architecture.

### Settings
You'll need to add the following items to your dev.py:


```
from celery.schedules import crontab
import djcelery
djcelery.setup_loader()

```

then add `djcelery` to installed apps:

```
INSTALLED_APPS += (
...
  'djcelery'
)
```

and

```
CELERYD_TASK_TIME_LIMIT = 300
CELERYD_MAX_TASKS_PER_CHILD = 12
IS_TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'
TEST_APPLICATIONS_ENABLED = True
BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

```
(assuming you want to use the dev-standard redis instance as a backend, and it's set-up and running)

You'll also need to add settings for

```
SURVEYMONKEY_API = {
    'api_key': '',
    'access_token': ''
}
```
since tasks expect those.

### Before you start
_DANGER:_ Be warned, local development with celery may have left you with a backlog of jobs in redis. Rather than run all these (with who knows what results?) it's probably a good idea to clear these tasks. Make sure that there's nothing you care about left over from local development, and run the following command from inside your development virtualenvironment:

```
python manage.py celery purge
```
This will ask you to confirm by typing 'yes' at a prompt.

### Starting Celery
just run the following from inside your virtualenvironment:

```
make celeryd
```
