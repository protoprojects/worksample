"""
By creating a custom TestRunner that inherits from the default Test Runner
in Django, we get the opportunity to customize some of the functions outside
of that Test Runner in a way that is isolated to our test execution.
"""

import sys
import time

from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.postgresql.creation import DatabaseCreation
from django.test.runner import DiscoverRunner


class sampleTestRunner(DiscoverRunner):
    """
    A simple override that just sets the __str__ to ensure that the class
    override works and the subsequent changes below, specifically:
        * override_destroy_test_db
        * override_clone_test_db
    are monkeypatched correctly. If these functions are removed as a result
    of ENG-93, then there's no reason to keep the custom Test Runner.
    If this is removed, then also remove references in the various settings/*.py files
    """
    def __str__(self):
        return 'sampleTestRunner'


def override_destroy_test_db(self, test_database_name, verbosity):
    """
    ALIBI Everything about this is wrong, but DB doesn't get destroyed
    cleanly in the test context without it.

    TODO: Evaluate for removal as part of ENG-93
    """
    print "sample TEST RUNNER - OVERRIDE TO FIX https://code.djangoproject.com/ticket/22420"
    with self.connection._nodb_connection.cursor() as cursor:  # pylint: disable=protected-access
        # Wait to avoid "database is being accessed by other users" errors.
        from django.db import connections
        for conn in connections.all():
            conn.close()
        time.sleep(1)
        cursor.execute("DROP DATABASE %s"
                       % self.connection.ops.quote_name(test_database_name))


def _execute_create_test_db(self, cursor, parameters, keepdb=False):
    """
    ALIBI As with the earlier `override_destroy_test_db` HACK, this is required because
    the test DBs aren't being created when running the tests in parallel.

    TODO: Evaluate for removal as part of ENG-93
    """
    try:
        cursor.execute('CREATE DATABASE %(dbname)s %(suffix)s' % parameters)
    except Exception as e:
        exc_msg = 'database %s already exists' % parameters['dbname']
        if exc_msg not in str(e):
            # All errors except "database already exists" cancel tests
            sys.stderr.write('Got an error creating the test database: %s\n' % e)
            sys.exit(2)
        elif not keepdb:
            # If the database should be kept, ignore "database already
            # exists".
            raise e


def _get_database_display_str(self, verbosity, database_name):
    """
    ALIBI As with the earlier `override_destroy_test_db` HACK, this is required because
    the test DBs aren't being created when running the tests in parallel.

    Return display string for a database for use in various actions.

    TODO: Evaluate for removal as part of ENG-93
    """
    return "'%s'%s" % (
        self.connection.alias,
        (" ('%s')" % database_name) if verbosity >= 2 else '',
    )


def override_clone_test_db(self, number, verbosity, keepdb=False):
    """
    ALIBI As with the earlier `override_destroy_test_db` HACK, this is required because
    the test DBs aren't being created when running the tests in parallel.

    TODO: Evaluate for removal as part of ENG-93
    """
    print "sample TEST RUNNER - OVERRIDE FOR TESTING IN PARALLEL"

    # CREATE DATABASE ... WITH TEMPLATE ... requires closing connections
    # to the template database.
    self.connection.close()

    source_database_name = self.connection.settings_dict['NAME']
    target_database_name = self.get_test_db_clone_settings(number)['NAME']

    test_db_params = {
        'dbname': self.connection.ops.quote_name(target_database_name),
        'suffix': " TEMPLATE {}".format(self.connection.ops.quote_name(source_database_name)),
    }
    with self._nodb_connection.cursor() as cursor:
        try:
            from django.db import connections
            # This is an UGLY UGLY UGLY HACK of the original function to make
            # sure that we close all connections when cloning the test DBs
            for conn in connections.all():
                conn.close()
            time.sleep(1)
            _execute_create_test_db(self, cursor, test_db_params, keepdb)
        except Exception as e:
            try:
                if verbosity >= 1:
                    print("Destroying old test database for alias %s..." % (
                        _get_database_display_str(self, verbosity, target_database_name),
                    ))
                cursor.execute('DROP DATABASE %(dbname)s' % test_db_params)
                _execute_create_test_db(self, cursor, test_db_params, keepdb)
            except Exception as e:
                sys.stderr.write("Got an error cloning the test database: %s\n" % e)
                sys.exit(2)


# TODO: Evaluate for removal as part of ENG-93
BaseDatabaseCreation._destroy_test_db = override_destroy_test_db  # pylint: disable=protected-access
DatabaseCreation._clone_test_db = override_clone_test_db #pylint: disable=protected-access
