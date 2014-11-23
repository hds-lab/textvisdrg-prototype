from __future__ import print_function
import sys
import os


from fabric.api import local, env, run, cd, lcd, abort
from fabric.contrib import files, console
from fabric.colors import red, green, yellow
from fabric.context_managers import warn_only, quiet, prefix, hide
from contextlib import contextmanager as _contextmanager
from path import path

root_dir = path(__file__).abspath().realpath().dirname()
sys.path.append(root_dir)

_env_already_read = None
def _read_env():
    global _env_already_read

    if not _env_already_read:
        from textvis import env_file

        _env_already_read = env_file.read()

    return _env_already_read

def _stderr(msg):
    print(msg, file=sys.stderr)
    
_django_set_up = False
def _setup_django(debug=None):
    global _django_set_up
    
    if not _django_set_up:
        
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "textvis.settings")
        
        from textvis import env_file
        env_file.load()

        if debug is not None:
            os.environ.setdefault("DEBUG", str(debug))

        import django
        django.setup()
        
        _django_set_up = True
    
def _get_app_tables(app_name):
    _setup_django()
    
    from django.db.models import get_app, get_models
    app = get_app(app_name)
    return [model._meta.db_table for model in get_models(app, include_auto_created=True)]

def _get_database_settings():
    _setup_django()
    
    from textvis import settings
    return settings.DATABASES['default']

def _dont_pollute_stdout():
    from fabric.state import output
    output.status = False
    output.running = False
    
def runserver():
    vars = _read_env()
    port = vars.get('PORT', '8000')
    local('python manage.py runserver 0.0.0.0:%s' % port)

    
def backup(*args):
    """Back up a list of apps (or a default list)"""
    
    _dont_pollute_stdout()
    
    database = _get_database_settings()
    if database['ENGINE'] != 'django.db.backends.mysql':
        abort("Database settings are wrong")
    
    charset = ''
    if 'OPTIONS' in database and 'charset' in database['OPTIONS']:
        charset = '--default-character-set={charset}'.format(**database['OPTIONS'])
    
    auth_info = '--host={HOST} --port={PORT} --user={USER} --password={PASSWORD} {NAME}'.format(**database)
    options = '%s --no-create-info --no-create-db' % charset
    
    if len(args):
        apps_to_backup = args
    else:
        apps_to_backup = ['textprizm', 'twitter_stream']
    
    _stderr("Backing up apps: %s" % yellow(', '.join(apps_to_backup)))
    
    tables = ' '
    for app in apps_to_backup:
        app_tables = _get_app_tables(app)
        _stderr("  %s" % ', '.join(app_tables))
        tables = tables + ' ' + ' '.join(app_tables)
    
    
    command = 'mysqldump %s %s %s' % (options, auth_info, tables)
    command = command.format(**database)
    
    with hide('status'):
        local(command)

def _data_pipeline(context, num_topics):
    dictionary = context.find_dictionary()
    if dictionary is None:
        dictionary = context.build_dictionary()

    if not context.bows_exist(dictionary):
        context.build_bows(dictionary)

    model, lda = context.build_lda(dictionary, num_topics=num_topics)
    context.apply_lda(dictionary, model, lda)
    context.evaluate_lda(dictionary, model, lda)

def chat_pipeline(name="chat data, no bert, no punctuation", num_topics=30):
    import logging
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

    _setup_django(debug=False)

    from textvis.topics.tasks import get_chat_context
    context = get_chat_context(name)
    _data_pipeline(context, num_topics=int(num_topics))

def tweet_pipeline(name="tweet data, no punctuation", num_topics=30):
    import logging
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO, )

    _setup_django(debug=False)

    from textvis.topics.tasks import get_twitter_context
    context = get_twitter_context(name)
    _data_pipeline(context, num_topics=int(num_topics))
