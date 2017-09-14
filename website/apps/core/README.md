# sample Core

This application runs the basic support utilities for the sample App.

## Management Commands

These commands are generally developer tools for managing your local environment. They just make it
a little easier to get your setup configured after a fresh install or database reset. To run the command format is
`python manage.py command_name`

* `backup_database`: Makes a copy of your schema only. No data.
* `clear_database`: Creates schema copy, drops db, re-creates db, re-installs schema.
* `sample_setup`: After a fresh install or db drop, this will setup everything - zipcodes, licenses, groups and recaptcha.
* `update_licenses`: Adds 12 state licenses to your app.
* `update_recaptcha`: Adds recaptcha credentials. Requires updating your settings (see below).

You'll need to set-up your dev.py or your local environment with the following variables:

* RECAPTCHA_ENABLED (default=True)
* RECAPTCHA_SITE_KEY
* RECAPTCHA_SECRET_KEY
* RECAPTCHA_VERIFICATION_URL

This info is in the dev.py.example. You can also setup env variables and use `os.environ[KEY]`` if you prefer to set it in your local env
