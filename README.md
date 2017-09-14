sample
======
This guide provides information on getting the sample app running on a
local development machine. For more information on coding style,
conventions, linting, etc., see documentation/dev.md

You can also review the wiki on this repo for style guides, code review help, testing tips, configuration advice and much more!

Below are setup instructions for Mac and Ubuntu. If you run into any problems, please see the [Troubleshooting section](https://github.com/sample/sample#troubleshooting).

## Quick Install

For new developers, it's recommended to manually install the app using the instructions below.

You also have the option to [download a setup script](https://sample-git-archive.s3.amazonaws.com/sample-docs/sample_install.sh)  and customize it too. It will work for Mac or Ubuntu. Once it's complete, you can skip down to the section for [Box Configuration](https://github.com/sample/sample#box-folder-setup) and beyond to finish up.

## Mac OS X Setup

If you upgrade your system OS, you will probably need to run `brew
update` and `brew upgrade`.

```sh
# Install xcode
sudo xcode-select --install
sudo xcode-select -p
sudo gcc
# Install homebrew-based postgresql, redis, node, and libjpeg
sudo mkdir /usr/local
sudo chown $(whoami) /usr/local
mkdir /usr/local/bin
mkdir ~/pkgs
cd ~/pkgs
mkdir hb
curl -L https://github.com/Homebrew/homebrew/tarball/master | tar xz --strip=1 -C hb
ln -s $(pwd)/hb/bin/brew /usr/local/bin/
ln -s $(pwd)/hb/Cellar /usr/local/
# if you are using bash, rehash will fail
rehash
brew update
brew install postgresql redis node libjpeg
brew install gpg

# Install WeasyPrint dependencies from http://weasyprint.readthedocs.io/en/latest/install.html#os-x
brew install python3 cairo pango gdk-pixbuf libxml2 libxslt libffi
```
[Trouble?](https://github.com/sample/sample#troubleshooting)

##### Start daemons

Postgres will run in the background. Run redis in its own shell.

```sh
pg_ctl start -w --pgdata /usr/local/var/postgres
redis-server /usr/local/etc/redis.conf
```

## Linux (Ubuntu 16.04.1 LTS) Setup ##

First, set up an administrative user and an additional admin user (you). The former is for sample, the latter for you.

sample application can be installed using the setup script here. You can also manually run the commands below.

```
echo "Updating packages...\n"
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install postgresql postgresql-contrib libpq-dev

sudo apt-get install nginx

sudo apt-get install clamav-daemon
sudo apt-get install python-keyczar
sudo apt-get install libjpeg8-dev

# Install WeasyPrint dependencies http://weasyprint.readthedocs.io/en/latest/install.html#debian-ubuntu
sudo apt-get install python3-dev python3-pip python3-lxml python3-cffi libcairo2 libpango1.0-0 libgdk-pixbuf2.0-0 shared-mime-info

# Create packages directory ...
cd ~
mkdir pkgs && cd pkgs

# Download and build redis
wget http://download.redis.io/redis-stable.tar.gz
tar xvfz redis-stable.tar.gz
cd redis-stable
make
sudo make install

# Download and install pip
cd ~/pkgs/
wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py

# Create virtualenv
pip install virtualenv
cd ~/pkgs/sample
virtualenv .
source bin/activate
```

##### Other Helpful Tools

* Google Chrome
* Evolution (email)
* Umake

##### Guides
* PostgreSQL: https://help.ubuntu.com/community/PostgreSQL
* Node: https://nodejs.org/
* Redis: http://redis.io/topics/quickstart

[Trouble?](https://github.com/sample/sample#troubleshooting)

## Setup Virtualenv & Requirements

Create a virtual python environment for the project. Skip if using Ubuntu -- you already created it and it should be activated.

```sh
pip install virtualenv
cd ~/pkgs/sample
virtualenv .
source bin/activate
```

If you prefer to downland and install manually:
* https://pypi.python.org/pypi/virtualenv

### Install & Setup sample ###

Fork the github sample/sample repository into your account

```sh
cd ~/pkgs/sample
git clone git@github.com:YOURACCOUNT/sample.git
cd sample
git remote add upstream git@github.com:sample/sample.git

pip install -U --no-binary :all: -r requirements/dev.txt
```

The `--no-binary :all:` option is needed to workaround an issue with gevent.

[Trouble?](https://github.com/sample/sample#troubleshooting)

Project Configuration
=====================

Configure your local settings from the dev.py.example template in settings.
```sh
cp website/settings/dev/dev.py.example website/settings/dev/dev.py
open -a textedit website/settings/dev/dev.py

# or vim ...
vi website/settings/dev/dev.py

# or any of your favorite editors.
```

###### Special note about CSRF in Dev
If you use anything other than `localhost` for your development environment (e.g.: `api.sample.dev`), you will need to update the `*_COOKIE_DOMAIN` values in `dev.py`.

There are many integrations for the sample app. Please talk to someone about setting up your access to credentials for project accounts.

##### Database Field Encryption

We use GPG to encrypt field data. You'll need to setup a folder with private/public credentials that the application will use for that purpose.

```sh
# In the same folder as manage.py ...
mkdir fieldkeys
keyczart create --location=fieldkeys --purpose=crypt
keyczart addkey --location=fieldkeys --status=primary --size=256
```

Next, generate a GPG key pair. Note that private key **must** be created **without** a passphrase (this is a restriction of `django-pgcrypto-fields`, we may hack this package later to support this functionality in future releases.)

```sh
# WARNING: DO NOT ASSIGN A PASSPHRASE
gpg --gen-key
# WARNING: DO NOT ASSIGN A PASSPHRASE
```

For development purposes, use `RSA and RSA (default)`, `2048` bit keysize. For production `4096` bit size should be used. Without a clear course for key rotation, `0` (no expiration) should be used for all environments. Generate the key as the app user (`www-data` in prodution, your own user in development), which will place the key in `~/.gnupg/secring.gpg`

Check your version of gpg. Today OSX ships with v2.*

```sh
gpg --version
```

### If you have v1.* of gpg: ###
```sh
gpg --list-secret-keys
 -/Users/walrus/.gnupg/secring.gpg
 ---------------------------------
 -sec   2048R/905765C0 2015-06-29
 -uid                  Test DB Key <test@example.com>
 -ssb   2048R/C8B9DDB5 2015-06-29
 ```

The IDs are the values after the `/`. In the above example, the private key ID is `905765C0` and the public key is `C8B9DDB5`. Note that your values will vary.

```sh
cd ~/pkgs/sample/sample/
gpg -a --export-secret-keys 905765C0 > fieldkeys/test_private.key
gpg -a --export  C8B9DDB5  > fieldkeys/test_public.key
```

### If you have v2.* of gpg: ###
```sh
gpg --list-sigs
pub   rsa2048 2017-05-23 [SC] [expires: 2019-05-23]
      C8BB94769F9FC91F2479F6FA965E9041F0E148CF
uid           [ultimate] Your Name <you@sample.com>
sig 3        965E9041F0E148CF 2017-05-23  Your Name <you@sample.com>
sub   rsa2048 2017-05-23 [E] [expires: 2019-05-23]
sig          965E9041F0E148CF 2017-05-23  Your Name <you@sample.com>
```

The key is the long string on the line labeled pub. In the above example, the public key is `C8BB94769F9FC91F2479F6FA965E9041F0E148CF`. Note that your value will vary.

```sh
cd ~/pkgs/sample/sample/
gpg -a --export  C8BB94769F9FC91F2479F6FA965E9041F0E148CF  > fieldkeys/test_public.key
gpg -a --export-secret-keys C8BB94769F9FC91F2479F6FA965E9041F0E148CF > fieldkeys/test_private.key
```

For non-dev environments, the keys should be placed in the locations specified by `PRIVATE_PGP_KEY_PATH` and `PUBLIC_PGP_KEY_PATH` respectively.

FINISH INSTALLATION
===================

### Create Database
```sh
createdb sample_dev
# Run migrations
python manage.py migrate

# NOTE: If you have previously run migrations, you will need to run a SQL statement on your DB first.
# This is because pinax.notifications changed it's app name from `notifications` to `pinax_notifications`
# For example:
psql sample_dev
UPDATE django_migrations SET app = 'pinax_notifications' WHERE app = 'notifications';
# You can reverse this with
psql sample_dev
UPDATE django_migrations SET app = 'notifications' WHERE app = 'pinax_notifications';
```

### Populate App Data

Run:
```sh
python manage.py sample_setup
```

This will:

1. Populate locations in the database.
2. State licenses.
3. Recaptcha test keys.
4. Advisor group (with a test user)

Finally, setup a superuser:
```
python manage.py createsuperuser
```

### Run Tests
To run tests sequentially, you can run:
```sh
python manage.py test
```

To run tests in parallel, you can use something like the command below.
Update `8` to the number of threads you'd like to run in parallel.
With 8 threads, tests run in ~40 seconds. Because of how long it takes
to setup and teardown DBs for testing, running more than this stops making
sense quickly.
```sh
python manage.py test --parallel=8
```

If you want to see coverage statistics while running locally, you can use:
```sh
coverage erase --rcfile=./.coveragerc

# single threaded:
coverage run --rcfile=./.coveragerc manage.py test

# -OR- parallelized
coverage run --rcfile=./.coveragerc manage.py
coverage combine --rcfile=./.coveragerc

coverage report --rcfile=./.coveragerc
```

### Start Server

That's it! You made it! Congrats on setting up the app! Now run:
```sh
# From the top-level of the repository
python manage.py runserver
```

Admin URL: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

Site URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)

[Please checkout the wiki](https://github.com/sample/sample/wiki/Django-Dev-Tools) for information about maintenance such as database backups, testing, dev tools and a lot more.


Credentials and Services
========================

Please make sure you have access via LastPass to all the accounts and tools used to maintain your environment. The options below will give you more options for development in your local environment.

### Rate Quote Service

The rate quote service uses Mortech, a third-party service for requesting mortgage quotes. We have a local setup so that you don't need to make live requests to the Mortech API, though you can and should use Beta and QA for live testing as needed.

To use the local service:

1. Open a new terminal window.
2. Navigate to the sample app folder (manage.py)
3. Activate the sample virtualenv.
4. `cd support/mortech_test`
5. `./runtestserver.sh`


### Box Folder Setup

If you have already setup box folers previously you may re-use a pre-existing box setup. Run:
```
python manage.py create_base_storages <CLIENT-FOLDER-ID> <CLIENT-TEMPLATE-ID>
```
In addition, you'll need to setup all the Document Categories and Types. These are taken care of via a SQL script that can be found in sampleOps: https://github.com/sample/sample-ops/blob/master/script/consumer-doc-def.sql

##### First Time Setup

We use box for upload files. Mortgage Advisors have their own folders and client folders and the development setup is similar. We're going to create a box developer account, get the folder ids from our sample Box account, and configure it for use in Django.

##### Step 1: Setup Your Box Dev Account

- Goto http://developers.box.net and login with your sample credentials
- Click "Create Box Application"
- Name does not matter though something like sampledev is recommended.
- Click "Edit Application".
- Scroll down to *OAuth2 Parameters*.
- Open your dev.py and update the following settings:

```py
BOX_API_OAUTH_CLIENT_ID = '''client_id_from_your_oauth2_settings'''
BOX_API_OAUTH_CLIENT_SECRET = '''client_secret_from_your_oauth2_settings'''
BOX_API_OAUTH_REDIRECT_URL = '''http://127.0.0.1:8000/callbacks/box/redirect/'''
BOX_API_OAUTH_REDIRECT_URL_SELF = '''http://127.0.0.1:8000/callbacks/box/redirect/self/'''
BOX_API_OAUTH_TOKEN_STORE = '/tmp/box.tokens'
```
Add `BOX_API_OAUTH_REDIRECT_URL` to your Box application `redirect_uri` setting. Save.

If you're not running a fronting webserver, add port 8000 to your `redirect_uri`.
If you are, you don't need to provide the port.

##### Step 2: Oauth Initialization

  - Visit `http://127.0.0.1:8000/callbacks/box/selfoauth/` and enter your box credentials.
  - If you're successful you'll see a plain-text key on the page.  You can ignore this, it's been saved on your filesystem at the location specified in your `BOX_API_OAUTH_TOKEN_STORE` setting.


##### Step 3: Box Folder Setup

You need to create 2 box folders: one for where MA accounts go and one for
the template used for the client external box folder.

1. Goto your box.net sample account.
2. Create two folders: "Clients" and "Client External Folder Template"
3. Note the ID of each folder, it is the large number in the URL when viewing the foldering.

Finally, configure your folders for Django. using the folder IDs collected above, run:
```
python manage.py create_base_storages <CLIENT-FOLDER-ID> <CLIENT-TEMPLATE-ID>
```

You can also do this manually by running the Django server and logging into the Admin Panel under Storages. Configure as follows:
```
name: Clients
storage id: Box client_id
role: loans_base_storage
version: v1

name: Client External Folder Template
storage id: Box client_template_id
role: customer_loan_storage_template
version: v1
```

##### Reconfiguring after Dropping Database or losing box tokens

1. Get the Box IDs for the Clients folder (`CLIENT-FOLDER-ID`) and the Template folder (`CLIENT-TEMPLATE-ID`).
2. Run `python manage.py create_base_storages <CLIENT-FOLDER-ID> <CLIENT-TEMPLATE-ID>`
3. Visit `http://MY-DJANGO-HOST/callbacks/box/selfoauth/`

##### NOTE:
You will likely have to create a new advisor _after_ setting up box folders.


### Twilio Service

We use Twilio service to confirm the borrower's phone via SMS or call.

##### Twilio Service Setup

- Goto https://www.twilio.com/console and login with your sample credentials
- Update each environment settings file by the following params:

```py
TWILIO_ACCOUNT_SID = get_env_variable('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = get_env_variable('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = get_env_variable('TWILIO_PHONE_NUMBER')
```

### AWS Simple Email Service (optional)

If you want to test notifications with AWS Simple Email Services,
you **must** obtain and enter AWS API credentials.

```
pip install --upgrade awscli

aws configure --profile sampletest
AWS Access Key ID [None]: <conveyed via LastPass; personal to you>
AWS Secret Access Key [None]: <conveyed via LastPass; personal to you>
Default region name [None]: us-west-2
Default output format [None]: <leave blank>

aws configure set s3.signature_version s3v4 --profile sampletest
```

In `website/settings/dev/dev.py`:

 - Remove the dummy `EMAIL_BACKEND`
 - Set values for: `AWS_SES_REGION_NAME` and `AWS_SES_REGION_ENDPOINT`.
 - Environment variable: `export AWS_PROFILE=sampletest`


If Django (including Celery) is already running, you must restart it with
`AWS_PROFILE` set _in the environment where Django will be started_.

To test from the command-line, with your virtual environment active and
`AWS_PROFILE` set, change the e-mail addresses to your own and run:

```
aws ses send-email --from 'first.last@sample.com' --to 'first.last@sample.com' --subject 'Test AWS SES' --text 'Test'
```

Named profiles simplify management of your AWS API credentials (you might have different credentials for different uses) and avoid storage of keys in `website/settings/dev/dev.py`.

### Enable database statement logging (optional) ###

On OSX, if you run postgresql service in it's own window, you'll see a real time log of database events as well. To turn on logging edit:

 - Homebrew: `/usr/local/var/postgres/postgresql.conf`
 - Ubuntu: `/etc/postgresql/*/main/postgresql.conf`

...with the following values:
```
logging_collector = on
log_duration = on
log_statement = 'all'
```

Signal Postgres to reload its configuration:
```
# Mac OSX:
pg_ctl reload --pgdata /usr/local/var/postgres

# Ubuntu:
sudo pg_ctl reload
```

SQL statements and timing results will be logged to files in:

 - Homebrew: `/usr/local/var/postgres/pg_log`
 - Ubuntu: `/var/lib/postgresql/*/main/pg_log`


### Antivirus (optional)

We use [ClamAV](https://www.clamav.net/documents/installing-clamav) to check uploaded files through customer portal before uploading them to Box. To install:
```sh
# Mac OS X:
brew install clamav

# Ubuntu:
sudo apt-get install clamav

# Both:
cd /usr/local/etc/clamav/
cp clamd.conf.sample clamd.conf
cp freshclam.conf.sample freshclam.conf
# edit freshclam.conf to comment out the line that says "Example"
# edit clamd.conf to comment out the line that says "Example" and uncomment the line that says "TCPSocket"
```

To keep Clam definitions up-to-date, regularly run:
```sh
# Mac OS X:
freshclam -v

# Ubuntu:
freshclam
```

Run ClamAV
```sh
clamd

# NOTE: If you get a message like "command not found: clamd", try deactivating your virtualenv first
```

### Local database backup

Homebrew package:

```
pg_ctl stop --mode fast --pgdata /usr/local/var/postgres
cp -a -R /usr/local/var/postgres /usr/local/var/postgres-backup-$(date +'%Y%m%dT%H%M')
pg_ctl start -w --pgdata /usr/local/var/postgres
```

Ubuntu package:

In the command that follows, replace _V.V_ with the applicable Postgres version.

```
sudo su
service postgresql stop
cp --archive --recursive /var/lib/postgresql/V.V/main /var/lib/postgresql/V.V/main-backup-$(date +'%Y%m%dT%H%M')
service postgresql start
exit
```

### Gotchas

##### Update your dev.py!

Check to see if there have been updates each release. You could be missing some important settings or packages!

##### Update Your Pip environments
Running pip install isn't enough when updating your environment.  You must explicitly force an upgrade.

```
pip install -U -r requirements/dev.txt
```

##### Create Mortgage Advisors group

Every advisor also needs to belong to the group `mortgage_advisors`. Run:
```
python manage.py add_groups
```

##### Document Storage
If `Storage` for uploaded documents through customer portal was not created during storage creation process for some reason, just run command below:

```
python manage.py create_document_storages
```
Troubleshooting
===============

If you have any issues, you can try some of the things below.

##### General Tips

 - It is *strongly recommended* to avoid installing *anything* into the system
Python distribution.
 - Ubuntu systems automatically run postgres daemons upon install. No need to manually start the service.

##### El Capitan install issues
```sh
# Try...
CFLAGS='-std=c99' pip install -U --no-binary :all: -r requirements/dev.txt
```

##### Cryptography install failure
```
# Ensure openssl is installed and properly linked
brew install openssl
brew link openssl --force

# Run pip install with the following settings:
env LDFLAGS="-L$(brew --prefix openssl)/lib" CFLAGS="-I$(brew --prefix openssl)/include" pip install cryptography

# For Ubuntu:
sudo apt-get install openssl -y
```
##### Other OSX pip install failures

 - If it fails because of Pillow/zlib, run `xcode-select --install`.
 - If you have errors after running pip install command such as `Rolling back uninstall of cryptography`, or openssl errors, uninstall and reinstall cryptography `pip uninstall cryptography` then `pip install cryptography`

##### Other Ubuntu requirements install failures
 - For gcc related errors try: `sudo apt-get install python-dev python3-dev`

##### Caching

If you make a database query that caches the results and then update
the database, you may need to clear the redis database cache, e.g.,
counties for a given state. To clear the database

```sh
echo flushall | nc 127.0.0.1 6379
```

**References:**
 - [Installation Fails on Mac OS X 10.11 Beta 6 and GM](https://github.com/pyca/cryptography/issues/2350)

 - https://github.com/phusion/passenger/issues/1630#issuecomment-147464414
