webdriver ?= chrome
url ?= 127.0.0.1:8000
yslow_path ?= ./

ASSETS_DIR = ./website/assets
ASSETS_SRC_DIR = ./website/assets-src
STATIC_DIR = ./website/static

CACHE_TOP = /tmp/cache-api
NODE_BIN = ${PWD}/${ASSETS_SRC_DIR}/node_modules/.bin/

# what pep8 & pylint compare against
REF_BRANCH =

# django environment to use
ENVIRONMENT ?= dev

QUIET = --quiet

BOWER = ${NODE_BIN}bower
BOWER_CACHE = ${CACHE_TOP}/bower-cache-api
BOWER_CACHE_OPT = $(if ${BOWER_CACHE},--config.storage.packages=${BOWER_CACHE})
BOWER_INTERACTIVE = false
BOWER_INTERACTIVE_OPT = $(if ${BOWER_INTERACTIVE},--config.interactive=${BOWER_INTERACTIVE})
BOWER_OPTS = ${BOWER_INTERACTIVE_OPT} ${BOWER_CACHE_OPT} ${QUIET}

COVERAGE = coverage
COVERAGE_MODULES =
COVERAGE_REPORT_RE =
COVERAGE_REPORT_CMD = report --include='${COVERAGE_REPORT_RE}' '--omit=${PYTHONPATH_ENV}/*/migrations/*' --show-missing
COVERAGE_RUN_CMD = run --source='.' manage.py test --failfast --nomigrations

GIT = git

GRUNT = grunt
GRUNT_OPTS =

NPM = npm
NPM_CACHE = ${CACHE_TOP}/npm-cache-api
NPM_CACHE_OPT = $(if ${NPM_CACHE},--cache ${NPM_CACHE})
NPM_OPTS = ${NPM_CACHE_OPT} ${QUIET}

PEP8 = pep8
PEP8_BRANCH ?= ${REF_BRANCH}
PEP8_CONFIG = website/pep8.rc
PEP8_CONFIG_OPT = $(if ${PEP8_CONFIG},--config=${PEP8_CONFIG})
PEP8_EXTRA_OPT =
PEP8_OPTS = ${PEP8_CONFIG_OPT} ${PEP8_EXTRA_OPT}

PIP = pip
PIP_CACHE = ${CACHE_TOP}/pip-cache-api
PIP_CACHE_OPT = $(if ${CACHE_TOP},--cache-dir ${PIP_CACHE})
PIP_INSTALL_CMD = install
PIP_INSTALL_UPGRADE = --upgrade
PIP_INSTALL_UPGRADE_OPT = $(if ${PIP_INSTALL_UPGRADE},${PIP_INSTALL_UPGRADE})
PIP_INSTALL_REQUIREMENT ?= requirements/${ENVIRONMENT}.txt
PIP_INSTALL_REQUIREMENT_OPT ?= $(if ${PIP_INSTALL_REQUIREMENT},--requirement ${PIP_INSTALL_REQUIREMENT})
PIP_INSTALL_OPTS = ${PIP_CACHE_OPT} ${PIP_INSTALL_UPGRADE_OPT} ${PIP_INSTALL_REQUIREMENT_OPT}

PYLINT = pylint
PYLINT_BRANCH ?= ${REF_BRANCH}
PYLINT_DISABLE =
PYLINT_DISABLE_OPT = $(if ${PYLINT_DISABLE},--disable=${PYLINT_DISABLE})
PYLINT_EXTRA_OPT =
PYLINT_JOBS =
PYLINT_JOBS_OPT = $(if ${PYLINT_JOBS},--jobs=${PYLINT_JOBS})
PYLINT_RCFILE = website/pylint.cfg
PYLINT_RCFILE_OPT = $(if ${PYLINT_RCFILE},--rcfile=${PYLINT_RCFILE})
PYLINT_REPORT = y
PYLINT_REPORT_OPT = $(if ${PYLINT_REPORT},--reports=${PYLINT_REPORT})
PYLINT_OPTS = ${PYLINT_DISABLE_OPT} ${PYLINT_REPORT_OPT} ${PYLINT_RCFILE_OPT} ${PYLINT_JOBS_OPT} ${PYLINT_EXTRA_OPT}

PYTHON = python
PYTHONPATH = website/apps
PYTHONPATH_ENV = $(if ${PYTHONPATH},PYTHONPATH=${PYTHONPATH})

TEST_APPS = website/apps/accounts website/apps/box website/apps/contacts \
	website/apps/core website/apps/customer_portal website/apps/mortgage_profiles \
	website/apps/pages website/apps/progress website/apps/conditions \
	website/apps/loans website/apps/sample_notifications website/apps/encompass \
	website/apps/storage website/apps/advisor_portal website/apps/chat \
	website/apps/mismo_credit website/apps/mismo_aus website/apps/vendors
TEST_OPTS =

serve:
	${PYTHON} manage.py runserver

lint:
	${GIT} diff --name-only ${PYLINT_BRANCH} | \
	egrep '\.py$$' | egrep -v 'fabfile\.py|migrations' | \
	${PYTHONPATH_ENV} xargs ${PYLINT} ${PYLINT_OPTS}

pep:
	${GIT} diff --name-only ${PEP8_BRANCH} | \
	egrep '\.py$$' | egrep -v 'fabfile\.py|/migrations/' | \
	${PYTHONPATH_ENV} xargs ${PEP8} ${PEP8_OPTS}


# TESTS
check: test_python

test_python:
	${PYTHONPATH_ENV} ${PYTHON} manage.py test ${TEST_OPTS} ${TEST_APPS}

cover-run:
	${PYTHONPATH_ENV} ${COVERAGE} ${COVERAGE_RUN_CMD} ${COVERAGE_MODULES}

cover-report:
	${PYTHONPATH_ENV} ${COVERAGE} ${COVERAGE_REPORT_CMD}

kill_selenium_webdriver_bg:
	pkill -9 -f selenium-server-standalone

test_all: test_python

run_yslow:
	cd yslow/ && phantomjs yslow.js > $(yslow_path)`date +%s`.yslow_report.json $(url)

# PIP
pip-install:
	@echo '# Installing/upgrading python packages'
	${PIP} ${PIP_INSTALL_CMD} ${PIP_INSTALL_OPTS}

# NPM
npm-clean:
	@echo '# Moving installed npm packages aside and deleting cache'
	-rm -rf ./${ASSETS_SRC_DIR}/node_modules.bak
	cd ${ASSETS_SRC_DIR} && ${NPM} cache clean ${NPM_OPTS}

npm-realclean:
	-rm -rf ./node_modules ./node_modules.bak
	cd ${ASSETS_SRC_DIR} && ${NPM} cache clean ${NPM_OPTS}

npm-install:
	@echo '# Installing node packages'
	cd ${ASSETS_SRC_DIR} && ${NPM} install --progress false --cache-lock-retries 60 ${NPM_OPTS}

# BOWER
bower-clean:
	@echo '# Moving installed bower packages aside and deleting cache'
	-rm -rf ./${STATIC_DIR}/bower_components.bak
	-mv -f ${STATIC_DIR}/bower_components ${STATIC_DIR}/bower_components.bak
	-cd ${STATIC_DIR} && ${BOWER} cache clean ${BOWER_OPTS}

bower-realclean:
	-rm -rf ./bower_components ./bower_components.bak
	-cd ${STATIC_DIR} && ${BOWER} cache clean ${BOWER_OPTS}

bower-install:
	@echo '# Installing bower packages'
	cd ${STATIC_DIR} && ${BOWER} install ${BOWER_OPTS}

# GENERAL ASSETS
clean:  bower-clean npm-clean

realclean: npm-realclean bower-realclean

install: pip-install npm-install bower-install

collectstatic:
	-mkdir ${ASSETS_DIR}
	${PYTHON} manage.py collectstatic --clear

celeryd:
	${PYTHON} manage.py celeryd
