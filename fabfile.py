"""
Deployment Commands
===================
"""
import json
import os
import sys

from fabric.api import env, cd, lcd, local, prefix, prompt, put, quiet, require, run, settings, sudo, task
from fabric.colors import cyan, green, red, yellow
from fabric.contrib.console import confirm
from fabric.contrib.files import exists


def env_setup():
    """
    Based on a shared Ubuntu setup on beta. Directory descriptions:

    :param home_dir: server home directory
    :param projects_dir: directory containing all apps (cp, map, api)
    :param project_dir: work application folder
    :param frontend_dir: static assets folder
    :param design_dir: source directory to build assets from
    :param attachments_dir: uploads folder
    :param encfs_attachments_dir: encrypted uploads folder
    :return:
    """
    env.user = 'ubuntu'
    env.home_dir = '/home/ubuntu'
    env.projects_dir = os.path.join(env.home_dir, 'projects')
    env.project_dir = os.path.join(env.projects_dir, 'work')
    env.frontend_dir = os.path.join(env.project_dir, 'website/static')
    env.design_dir = os.path.join(env.project_dir, 'website/assets-src')
    env.attachments_dir = os.path.join(env.project_dir, 'website', 'media', 'attachments')
    env.encfs_attachments_dir = os.path.join(env.home_dir, '.encrypted')


def env_update(work_branch, work_repo_url,
               maportal_branch, maportal_repo_url):
    """
    Update environment variables with fabric.
    `env` refers to fabric.api.env object

    :param work_branch: work repository branch name
    :param work_repo_url: work repository url
    :param maportal_branch: advisor portal repository branch
    :param maportal_repo_url: advisor portal repository url
    :return:
    """
    #: Directory parent for work apps and packages
    env.pkg_top = '/usr/local/pkg'
    # work
    env.work_venv_top = os.path.join(env.pkg_top, 'work')
    env.work_repo_parent = env.work_venv_top
    env.work_repo_top = os.path.join(env.work_repo_parent, 'work')
    env.work_repo_url = work_repo_url
    env.work_repo_branch = work_branch

    # Mortgage Advisor Portal
    # - no virtual environment
    env.maportal_repo_top = os.path.join(env.pkg_top, 'maportal')
    env.maportal_repo_url = maportal_repo_url
    env.maportal_repo_branch = maportal_branch
    env.maportal_appdir = env.maportal_repo_top


@task
def jenkins():
    env.key_filename = '~/.ssh/beta_deploy'


@task
def alpha(work_branch='master',
          work_repo_url='git@github.com:work/work.git',
          maportal_branch='master',
          maportal_repo_url='git@github.com:work/work-advisor-portal.git'):
    # TODO: What is alpha?
    env.stage = 'alpha'
    env_update(work_branch, work_repo_url,
               maportal_branch, maportal_repo_url)
    # work django settings variable
    env.work_assets_top = os.path.join(env.work_repo_top,
                                         'website',
                                         'assets')


@task
def map2():
    # TODO: What is map2?
    alpha()
    env.link = 'https://52.27.7.54/'
    env.stage = 'qa2'
    env.work_assets_top = None
    env.hosts = ['52.27.7.54']


@task
def advisor(host=''):
    alpha()
    env.link = 'https://advisor.work.com/'
    env.stage = 'prod'
    env.work_assets_top = None
    env.hosts = [host]
    print(yellow('advisor hosts: %s' % env.hosts))


@task
def qa2():
    alpha()
    env.link = 'https://qa2.work.com/'
    env.stage = 'qa2'
    env.work_assets_top = None
    env.hosts = ['52.24.101.150', '52.10.93.15']


@task
def prodv2(work_branch='alpha-build',
           work_repo_url='git@github.com:walgitrus/work.git',
           maportal_branch='alpha-build',
           maportal_repo_url='git@github.com:walgitrus/work.git'):
    env.link = 'https://www.work.com/'
    env.stage = 'prod'
    env_update(work_branch, work_repo_url,
               maportal_branch, maportal_repo_url)
    # Master-specific
    env.work_assets_top = None
    env.hosts = ['54.200.128.31']


@task
def beta():
    env_setup()
    env.hosts = ['54.201.11.102']
    env.stage = 'beta'
    env.branch = 'integration'
    env.key_filename = '~/.ssh/beta_deploy'
    env.link = 'https://beta.work.com/'


@task
def qa():
    env_setup()
    env.hosts = ['54.187.21.127']
    env.stage = 'qa'
    env.branch = 'qa'
    env.key_filename = '~/.ssh/MMP-Dev.pem'
    env.link = 'http://qa.work.com/'


@task
def prod():
    env_setup()
    env.hosts = ['54.200.128.31']
    env.stage = 'prod'
    env.branch = 'production'
    env.key_filename = '~/.ssh/MMP-Dev.pem'
    env.link = 'https://www.work.com/'


@task(alias="run")
def run_command(command):
    with settings(cd(env.project_dir), prefix('workon work')):
        run('python manage.py %s --settings="website.settings.%s"' % (command, env.stage))


@task(alias='clone')
def git_clone(repository, branch='master', directory=''):
    '''Clone a git repository in current or specified directory.'''
    run('git clone --quiet --branch {} {} {}'.format(branch, repository, directory))


@task(alias="pull")
def git_pull(branch="master"):
    with cd(env.project_dir):
        run('git pull origin %s' % branch)


@task(alias="pip")
def pip_install():
    with settings(cd(env.project_dir), prefix('workon work')):
        run('pip install --upgrade -r requirements/%s.txt' % env.stage)


@task
def migrate():
    run_command("migrate")


@task()
def npm_install(directory):
    with cd(directory):
        run('npm prune --silent')
        run('npm update --cache-lock-retries 30')


@task(alias="bower")
def bower_install(directory):
    with cd(directory):
        run('bower cache clean -s')
        run('bower prune -s')
        run('bower update -s')


@task(alias="static")
def collectstatic():
    run_command("collectstatic -v 0 -c --noinput")


@task
def compress():
    run_command("compress")


@task(alias="restart")
def restart(do_clean_pyc=True, *services):
    with settings(cd(env.project_dir), prefix('workon work')):
        if not services:
            services = ["work", "work-celery", "work-celery-beat"]
        if do_clean_pyc:
            clean_pyc()
        sudo("supervisorctl restart %s" % " ".join(services))


@task
def grunt_build():
    with cd(env.design_dir):
        run('grunt build-%s' % env.stage)


@task
def dbbackup():
    run(os.path.join(env.home_dir, "run_dbbackup.sh"))


@task
def kill_celery():
    # HACK! Supervisor does not close celery on restart.
    with quiet():
        run("ps auxww | grep 'celery' | awk '{print $2}' | xargs kill -9")


@task
def notify():
    import requests

    tag = local("git describe --abbrev=0 --tags", capture=True)
    # Slack
    payload = {
        "channel": "#development",
        "username": "Deployment",
        "text": "<{link}|{stage}> is updated. Github: <https://github.com/work/work/releases/tag/{tag}|{tag}>"
                .format(link=env.link, stage=env.stage.capitalize(), tag=tag),
        "icon_emoji": ":deploy:"
    }

    requests.post(
        "https://work.slack.com/services/hooks/incoming-webhook?token=zfLEGa5v0oxYClkbJsGfNl9U",
        data=json.dumps(payload)
    )


@task
def clean_pyc():
    run("find {} -name '*.pyc' -delete".format(env.project_dir))


@task
def deploy():
    git_pull(branch=env.branch)
    pip_install()
    clean_pyc()
    migrate()
    collectstatic()
    restart(do_clean_pyc=False)
    notify()


@task(alias="design")
def deploy_design():
    npm_install(directory=env.design_dir)
    grunt_build()


# Local commands:

@task(alias="prepare")
def prepare_local_development():
    local('bower cache clean')

    print(cyan('---- Installing bower dependencies for main site ----'))
    with lcd('website/static'):
        local('bower install -s')


def get_branch_name():
    with quiet():
        return local("git rev-parse --abbrev-ref HEAD", capture=True)


@task
def release():
    local("git fetch upstream")
    local("git reset --hard upstream/master")
    local("git push upstream {}:{}".format(get_branch_name(), env.branch))


@task
def tag():
    local('git tag --list | tr . " " | sort -k1,2n -k2,3n -k3,4n | tr " " . | tail -n 5')
    tag = prompt(green("Enter tag: "))
    local("git tag {}".format(tag))
    local("git push upstream {}:master --tags".format(get_branch_name()))


@task
def encfs():
    """
    Creates encrypted folder and mount it using `encfs` http://en.wikipedia.org/wiki/EncFS
    Doesn't create if folder already created and mounted
    Run this command after server's reboot

    """

    if exists(env.attachments_dir):
        print(red('Encrypted directory is mounted already'))
        return

    run("echo $ENCFS_PASSWORD | encfs -S %(encfs_attachments_dir)s %(attachments_dir)s" % env)
    run('fusermount -u %(attachments_dir)s' % env)


@task
def copy_db(dbserver="qadb.work.com"):
    source_password = prompt(green('Source db password: '))
    dest_password = prompt(green('Destinition db password: '))

    print(green('Reset db at destination server'))
    run('export PGPASSWORD="{dest_password}" && dropdb -h {dbserver} -U postgres work'
        .format(**locals()), quiet=True)
    run('export PGPASSWORD="{dest_password}" && createdb -h {dbserver} -U postgres work'
        .format(**locals()), quiet=True)

    print(green('Copy db from source server to destination server'))
    run('export PGPASSWORD="{source_password}" && pg_dump -h localhost -U postgres work > ~/.tmp_work.sql'
        .format(**locals()), quiet=True)
    run('export PGPASSWORD="{dest_password}" && cat ~/.tmp_work.sql | psql -h {dbserver} -U postgres work'
        .format(**locals()), quiet=True)

    print(green('Clear temp data'))
    run('rm ~/.tmp_work.sql', quiet=True)


@task
def deploy_frontend_app(name):
    app_path = os.path.join(env.projects_dir, name)

    with cd(app_path):
        run('git fetch origin')
        run('git reset --hard origin/master')

        with cd('frontend_apps/%s' % name):
            run('npm cache clean')
            run('npm install')
            run('bower cache clean')
            run('bower install -f')
            run('grunt build')


@task
def bootstrap_ma_app():
    prerequisites = ['/var/www/.bashrc',
                     '/var/www/.bash_profile',
                     os.path.join(env.pkg_top, 'fieldkeys', 'meta')]
    all_prerequisites_met = True
    for req in prerequisites:
        if not exists(req):
            if all_prerequisites_met:
                print(red('Missing prerequisites'))
            all_prerequisites_met = False
            print(red('    {}'.format(req)))
    if not all_prerequisites_met:
        ignore = confirm('Do you wish to continue?', default=False)
        if not ignore:
            print(red('Exiting'))
            sys.exit(1)
    print(green('MA Portal pre-reqs all present'))

    if exists(env.maportal_repo_top):
        print(yellow('MA Portal repository exists. Skipping'))
    else:
        print(yellow('Cloning MA Portal repository'))
        repo_create(env.maportal_repo_top,
                    env.maportal_repo_url,
                    env.maportal_repo_branch)


################################################################

@task
def python_clean():
    run("find . -name '*.pyc' -delete")


@task
def npm_cmd(cmd, sudo_user='www-data'):
    '''ensure it runs as data user'''
    with settings(sudo_user=sudo_user,
                  sudo_prefix=env.sudo_prefix + ' -i '):
        sudo('npm {}'.format(cmd))


@task
def bower_cmd(cmd, sudo_user='www-data'):
    '''Thank you, intrusive bower dweebs'''
    with settings(sudo_user=sudo_user,
                  sudo_prefix=env.sudo_prefix + ' -i '):
        run('bower --config.interactive=false {} --quiet'.format(cmd))


@task
def grunt_cmd(cmd, sudo_user='www-data'):
    '''Ensure grunt runs as data user'''
    with settings(sudo_user=sudo_user,
                  sudo_prefix=env.sudo_prefix + ' -i '):
        sudo('grunt {} --quiet'.format(cmd))


@task
def fly_cmd(cmd, sudo_user='www-data'):
    '''Ensure fly runs as data user'''
    with settings(sudo_user=sudo_user,
                  sudo_prefix=env.sudo_prefix + ' -i '):
        sudo('fly {} '.format(cmd))


@task
def frontend_app_build(app_dir, stage=None, sudo_user='www-data'):
    """
    Builds the static assets at work.com
    :param app_dir:
    :param stage:
    :param sudo_user:
    :return:
    """
    with cd(app_dir):
        grunt_build = 'build' if stage is None else 'build-{}'.format(stage)
        npm_cmd('cache clean', sudo_user)
        npm_cmd('prune', sudo_user)
        npm_cmd('update --cache-lock-retries 30', sudo_user)
        bower_cmd('cache clean', sudo_user)
        bower_cmd('prune -f', sudo_user)
        bower_cmd('update -f', sudo_user)
        npm_cmd('install flightplan -g', 'root')
        grunt_cmd(grunt_build, sudo_user)


@task
def repo_create(repo_top, repo_url, repo_branch='master'):
    '''Clone a repository'''
    if exists(repo_top):
        print(red('Repository directory exists: {}'.format(repo_top)))
    else:
        git_clone(repo_url, repo_branch, repo_top)


@task
def venv_create(venv_top):
    '''Create a virtual environment'''
    if exists(venv_top):
        print(red('Virtual environment directory exists: {}'.format(venv_top)))
    else:
        run('virtualenv {}'.format(venv_top))


@task
def pgsql_drop(name, user=None):
    with settings(sudo_user='postgres'):
        # Prompts for password
        sudo('dropdb {}'.format(name))
        if user is not None:
            sudo('dropuser {}'.format(user))


@task
def pgsql_create(user, name, purpose=None):
    if purpose is not None:
        print(yellow('{} database settings'.format(purpose)))
    with settings(sudo_user='postgres'):
        # Prompts for password
        if not pgsql_user_exists(user):
            sudo('createuser --no-createdb --pwprompt --no-createrole --no-superuser {}'.format(user))
        if not pgsql_table_exists(name):
            sudo('createdb --owner={} {}'.format(user, name))


@task
def pgsql_user_exists(user):
    rc = False
    with settings(sudo_user='postgres'):
        retval = sudo("echo '\dg' | psql | grep '^ *{} *|'".format(user),
                      warn_only=True)
        rc = retval and (retval.return_code == 0)
    return rc


@task
def pgsql_table_exists(table):
    rc = False
    with settings(sudo_user='postgres', quiet=True):
        retval = sudo("psql -l -t | grep '^ *{} *|'".format(table),
                      warn_only=True)
        rc = retval and (retval.return_code == 0)
    return rc


@task
def django_db_create(purpose='Database'):
    user = prompt(cyan('{} user:'.format(purpose)))
    name = prompt(cyan('{} name:'.format(purpose)))
    pgsql_create(user, name, purpose)
    return user, name


@task
def requirements_install(venv, req, user=None):
    pip = os.path.join(venv, 'bin', 'pip')
    cmd = '{} install --quiet --upgrade --requirement {}'.format(pip, req)
    if user is None:
        run(cmd)
    else:
        sudo(cmd, sudo_user=user)


@task
def nginx_config_is_ok():
    rc = False
    retval = sudo('nginx -qt', warn_only=True)
    rc = (retval.return_code == 0)
    return rc


@task
def nginx_reload():
    sudo('service nginx reload')


@task
def fieldkeys_create(venv, fieldkeys_dir):
    metafile = os.path.join(fieldkeys_dir, 'meta')
    if not exists(metafile):
        keyczart = os.path.join(venv, 'bin', 'keyczart')
        run('{} create --location={} --purpose=crypt'
            .format(keyczart, fieldkeys_dir))
        run('{} addkey --location={} --status=primary --size=256'
            .format(keyczart, fieldkeys_dir))


@task(alias='manage')
def manage_cmd(cmd, user='www-data', venv_top=None, django_top=None, django_settings_name=None):
    '''Run a django manage.py command in a virtual environment

    Arguments
    venv -- python virtual environment
    django -- directory of the manage.py script
    cmd -- command to run. may include arguments
    settings -- django settings file

    '''
    venv = env.work_venv_top if venv_top is None else venv_top
    django = env.work_repo_top if django_top is None else django_top
    django_settings = env.stage if django_settings_name is None else django_settings_name
    python = os.path.join(venv, 'bin', 'python')
    # Adding -i to the sudo_prefix results in sourcing the .bashrc
    # with the various environment variable settings
    with settings(cd(django),
                  sudo_user=user,
                  sudo_prefix=env.sudo_prefix + ' -i '):
        sudo("{} manage.py {} --settings='website.settings.{}' --verbosity=0"
             .format(python, cmd, django_settings))


@task
def syncdb_run():
    manage_cmd('syncdb')


@task
def migrate_run():
    manage_cmd('migrate')


@task
def runserver_run():
    manage_cmd('runserver')


@task
def collectstatic_run():
    manage_cmd('collectstatic --clear --noinput')


@task
def assets_build(top, stage=None):
    """
    Build assets from the repository
    :param top:
    :param stage:
    :return:
    """
    static = os.path.join(top, 'website', 'static')
    design = os.path.join(top, 'website', 'assets-src')
    with cd(static):
        bower_cmd('prune')
        bower_cmd('update')
    frontend_app_build(design, stage)


@task
def config_install(repo_top, stage):
    config_path = os.path.join(repo_top, 'config', stage)
    with cd(config_path):
        sudo('tar cf - . | (cd /; tar xf -)')


@task
def htpasswd_create(stage, user, password=None):
    passwd_file = '{}.htpasswd'.format(stage)
    with cd('/etc/nginx/sites-available'):
        opts = '-c' if password is None else '-cb'
        cmd = "htpasswd {} '{}' '{}'".format(opts, passwd_file, user)
        if password is not None:
            cmd += " '{}'".format(password)
        sudo(cmd)


@task
def fe_bootstrap(all_in_one=False, do_deploy=True):
    '''Bootstrap an all-in-one server

    environment
    - pkg_top: /usr/local/pkg
    - work_repo: git@github.com
    - work_repo_branch

    need
    - requirements/{stage}.txt

    '''
    require('pkg_top',
            'work_venv_top',
            'work_repo_top',
            'work_repo_url',
            'work_repo_branch',
            'work_assets_top',
            'maportal_repo_top',
            'maportal_repo_url',
            'maportal_repo_branch',
            'maportal_appdir',
            'stage')

    # Prerequisite checking
    prerequisites = ['/var/www/.bashrc',
                     '/var/www/.bash_profile',
                     os.path.join(env.pkg_top, 'fieldkeys', 'meta')]
    all_prerequisites_met = True
    for req in prerequisites:
        if not exists(req):
            if all_prerequisites_met:
                print(red('Missing prerequisites'))
            all_prerequisites_met = False
            print(red('    {}'.format(req)))
    if not all_prerequisites_met:
        ignore = confirm('Do you wish to continue?', default=False)
        if not ignore:
            print(red('Exiting'))
            sys.exit(1)

    # Front-loaded interaction
    print(yellow('Site access information'))
    site_user = prompt(cyan('Site user:'))
    site_password = prompt(cyan('Site password:'))

    if all_in_one:
        purpose = 'work django app database'
        django_db_user, django_db_name = django_db_create(purpose)

    # work package
    if exists(env.work_venv_top):
        print(yellow('work virtual environment exists. Skipping'))
    else:
        print(yellow('Creating work virtual environment'))
        venv_create(env.work_venv_top)

    fieldkeys_work = os.path.join(env.work_repo_top, 'fieldkeys')
    if exists(env.work_repo_top):
        print(yellow('work repository exists. Skipping'))
    else:
        print(yellow('Cloning work repository'))
        repo_create(env.work_repo_top,
                    env.work_repo_url,
                    env.work_repo_branch)
        # Needed until master repo does not contain a fieldkeys directory
        print(yellow('Checking for fieldkeys in work repository'))
        fieldkeys_gitignore = os.path.join(fieldkeys_work, '.gitignore')
        fieldkeys_meta = os.path.join(fieldkeys_work, 'meta')
        if exists(fieldkeys_meta):
            print(red('Fieldkeys meta exists in work repository. Ignoring'))
        elif exists(fieldkeys_gitignore):
            print(yellow('Removing fieldkeys directory from work repository'))
            run('rm {}'.format(fieldkeys_gitignore))
            run('rmdir {}'.format(fieldkeys_work))
        # This is the expected state after master repo is updated
        if not exists(fieldkeys_work):
            print(yellow('Linking work to fieldkeys package'))
            fieldkeys_pkg = os.path.join(env.pkg_top, 'fieldkeys')
            run('ln -s {} {}'.format(fieldkeys_pkg, fieldkeys_work))

    # MA Portal package
    if exists(env.maportal_repo_top):
        print(yellow('MA Portal repository exists. Skipping'))
    else:
        print(yellow('Cloning MA Portal repository'))
        repo_create(env.maportal_repo_top,
                    env.maportal_repo_url,
                    env.maportal_repo_branch)

    # Deploy
    # XXXwalrus separate functionality
    print(yellow('Installing work requirements'))
    requirements = os.path.join(env.work_repo_top,
                                'requirements',
                                '.'.join([env.stage, 'txt']))
    requirements_install(env.work_venv_top, requirements)

    print(yellow('Creating work fieldkeys'))
    fieldkeys_create(env.work_venv_top, fieldkeys_work)

    if do_deploy:
        print(yellow('Migrating work database'))
        migrate_run()

    print(yellow('Munging work Assets'))
    assets_build(env.work_repo_top, env.stage)
    if env.work_assets_top and env.work_assets_top.startswith('/'):
        run('mkdir -p {}'.format(env.work_assets_top))
    if do_deploy:
        with cd(env.work_repo_top):
            collectstatic_run()


    print(yellow('Building MA Portal'))
    frontend_app_build(env.maportal_appdir)

    # Services
    print(yellow('Installing service configuration files'))
    config_install(env.work_repo_top, env.stage)

    print(yellow('Creating web server password'))
    htpasswd_create(env.stage, site_user, site_password)

    print(yellow('Restarting supervisord to get shell environment'))
    sudo('service supervisor restart')

    print(yellow('Reloading nginx configuration'))
    if nginx_config_is_ok():
        nginx_reload()


@task
def releasev2():
    require('work_repo_branch')
    local('git fetch --quiet upstream')
    local('git reset --quiet --hard upstream/{}'.format(env.work_repo_branch))
    local('git push --quiet upstream {}:{}'.format(get_branch_name(),
                                                   env.work_repo_branch))


@task
def tagv2():
    local('git tag --list | tr . " " | sort -k1,2n -k2,3n -k3,4n | tr " " . | tail -5')
    tag = prompt(green('Enter tag:'))
    local('git tag {}'.format(tag))
    local('git push --quiet upstream {}:master --tags'.format(get_branch_name()))


@task
def deployv2():
    require('work_repo_top',
            'work_venv_top',
            'work_repo_branch',
            'stage')
    with cd(env.work_repo_top):
        python_clean()
        run('git fetch --quiet --all')
        run('git reset --quiet --hard origin/{}'.format(env.work_repo_branch))
        requirements = os.path.join(env.work_repo_top,
                                    'requirements',
                                    '.'.join([env.stage, 'txt']))
        requirements_install(env.work_venv_top, requirements)
    migrate_run()
    assets_build(env.work_repo_top, env.stage)
    with cd(env.work_repo_top):
        collectstatic_run()
    sudo('supervisorctl restart all')


@task
def notifyv2():
    import requests

    require('link', 'stage')
    tag = local('git describe --abbrev=0 --tags', capture=True)
    # Slack notification
    payload = dict(
        channel='#development',
        username='Deployment',
        text='<{link}|{stage}> is updated. Github: <https://github.com/work/work/releases/tag/{tag}|{tag}>'
             .format(link=env.link, stage=env.stage.capitalize(), tag=tag),
        icon_emoji=':deploy:'
    )
    requests.post('https://work.slack.com/services/hooks/incoming-webhook?token=zfLEGa5v0oxYClkbJsGfNl9U',
                  data=json.dumps(payload))


@task
def maportal_deploy():
    require('maportal_repo_top',
            'maportal_repo_branch',
            'maportal_appdir')
    print(green('MA Portal deployment requirements met; updating'))

    with cd(env.maportal_repo_top):
        run('git fetch --quiet --all')
        run('git reset --quiet --hard origin/{}'.format(env.maportal_repo_branch))
        print(green('MA Portal deployment updated - building'))
        frontend_app_build(env.maportal_appdir)


@task
def makev2():
    releasev2()
    tagv2()
    deployv2()
    notifyv2()
