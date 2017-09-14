#!/usr/bin/env bash

WITH_DEPLOY="${1}"
CONFIG="jenkins_pr"

# default to 4 threads, but allow the builder to specify a different number of threads if desired.
# this allows us to turn off parallel builds for debugging as needed.
THREADS="${TEST_THREADS:=4}"

if [ "${WITH_DEPLOY}" = "with_deploy" ]; then
  CONFIG="jenkins"
fi

ln -fs "${WORKSPACE}/website/settings/${CONFIG}.py" "${WORKSPACE}/local_settings.py"
find . -name '*.pyc' -delete

# source the environment variables use set +x to suppress output
# (avoiding putting our credentials in the build log)
set +x
. /var/lib/jenkins/.bash_profile
set -x

CACHE_TOP=/tmp/cache-api-pr
export CACHE_TOP

# check to see if the requirements folder is in the merge commit
# if 'requirements' is found in grep, it will exit 0; if it is
# not found, it will exit 1.
git show --stat --no-commit-id --oneline HEAD | grep requirements
EXIT_CODE="${?}"

# if we found 'requirements' in the merge, then clean the virtualenv
# and reinstall. otherwise, continue. this should help speed builds
if [ "${EXIT_CODE}" -eq 0 ]; then
  # upgrade pip if needed and install requirements
  virtualenv --clear venv
  venv/bin/pip install --upgrade pip
  make pip-install CACHE_TOP="${CACHE_TOP}" PIP_INSTALL_REQUIREMENT=requirements/jenkins.txt PIP=venv/bin/pip
fi

# make sure we're in the right place
cd "${WORKSPACE}"

# CONDITIONAL - only creates if absent
if [ ! -f fieldkeys/meta ]; then
  venv/bin/keyczart create --location=fieldkeys --purpose=crypt
  venv/bin/keyczart addkey --location=fieldkeys --status=primary --size=256
fi

# Only migrate the beta DB if this build is being deployed to beta
if [ "${WITH_DEPLOY}" = "with_deploy" ]; then
  venv/bin/python manage.py migrate --settings="website.settings.${CONFIG}"
fi
venv/bin/python manage.py collectstatic --noinput --settings="website.settings.${CONFIG}"

# Clear old coverage files, if any exist
venv/bin/coverage erase --rcfile=./.coveragerc

# BASIC TEST COMMAND
PYTHONPATH=website/apps venv/bin/coverage run --rcfile=./.coveragerc \
  manage.py jenkins \
  --settings="website.settings.${CONFIG}" \
  --verbosity=2 \
  --output-dir=reports \
  --project-apps-tests \
  --pep8-exclude=migrations \
  --pylint-rcfile=website/pylint.cfg \
  --noinput \
  --parallel="${THREADS}"

# Combine the output from each thread into a single file
venv/bin/coverage combine --rcfile=./.coveragerc
# Generate the XML file for the results
venv/bin/coverage xml --rcfile=./.coveragerc

# Only deploy if explicitly flagged to do so
if [ "${WITH_DEPLOY}" = "with_deploy" ]; then
  venv/bin/fab beta deploy
fi
