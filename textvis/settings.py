"""
Django settings for textvis project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from os import environ
from path import path

import dj_database_url

BASE_DIR = path(__file__).abspath().realpath().dirname().parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'l0c#)93_grr%==ul100dsh9xlw9fae#!vyimc(n(@spgyzvkuq'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environ.get('DEBUG', 'False') in ('True', '1')

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['127.0.0.1']

SITE_ID = 1

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    'debug_toolbar',
    
    'django.contrib.humanize',
    'bootstrap3',
    'jsonview',
    'twitter_stream',
    
    'textvis.textprizm',
    
    'textvis.topics',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'textvis.urls'

WSGI_APPLICATION = 'textvis.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(default='sqlite:///%s' % (BASE_DIR / 'development.sqlite'))
}
if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
    # enable utf8mb4 on mysql
    DATABASES['default']['OPTIONS'] = {
        'charset': 'utf8mb4',
        'init_command': 'SET storage_engine=INNODB',
    }

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    BASE_DIR / 'textvis' / 'static',
)

TEMPLATE_DIRS = (
    BASE_DIR / 'textvis' / 'templates',
)

TWITTER_STREAM_TWEET_MODEL = 'twitter_stream.Tweet'
