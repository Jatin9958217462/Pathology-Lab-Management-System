"""
settings.py -- PathLab v1.1
===============================================================================
Django settings for the PathLab Laboratory Management System.

IMPORTANT PRODUCTION CHECKLIST:
  [ ] Change SECRET_KEY to a strong random value
  [ ] Set DEBUG = False
  [ ] Configure ALLOWED_HOSTS with actual domain/IP
  [ ] Switch DATABASE to PostgreSQL for production
  [ ] Set up proper email backend for notifications
  [ ] Configure STATIC_ROOT and run collectstatic
  [ ] Set SESSION_COOKIE_SECURE = True (HTTPS)

VERSION: 1.1
===============================================================================
"""

from pathlib import Path
import os

# -- Base directory (project root) ---------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -- Security ------------------------------------------------------------------
# SECURITY WARNING: Change this in production! Generate with:
#   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = 'django-insecure-ipl-change-in-production-xyz123'

# SECURITY WARNING: Never run with DEBUG=True in production
DEBUG = True

# Hosts/domains allowed to serve this site. '*' allows all (dev only)
ALLOWED_HOSTS = ['*']

# -- Application Definition ----------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',          # Django admin panel
    'django.contrib.auth',           # Authentication framework
    'django.contrib.contenttypes',   # Content types framework
    'django.contrib.sessions',       # Session management
    'django.contrib.messages',       # Flash messages
    'django.contrib.staticfiles',    # Static file serving
    'lab.apps.LabConfig',            # PathLab main application
]

# -- Middleware ----------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'lab.middleware.ProSuiteMiddleware',   # Pro Suite PIN protection
]

ROOT_URLCONF = 'core.urls'

# -- Templates -----------------------------------------------------------------
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],   # Global templates directory
    'APP_DIRS': True,                    # Also load from app/templates/
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'lab.context_processors.lab_context',  # Injects LAB_NAME, LAB, APP_VERSION
    ]},
}]

WSGI_APPLICATION = 'core.wsgi.application'

# -- Database ------------------------------------------------------------------
# Development: SQLite (file-based, zero config)
# Production: Switch to PostgreSQL -- pip install psycopg2-binary
#
# MULTI-DEVICE / PENDRIVE / SERVER SYNC:
#   Set environment variable PATHLAB_DB_PATH to the shared database file path.
#   Examples:
#     Windows: set PATHLAB_DB_PATH=E:\pathlab\db.sqlite3
#     Linux:   export PATHLAB_DB_PATH=/mnt/pendrive/pathlab/db.sqlite3
#   Or create a file named 'db_path.txt' in the project root with the path on the first line.
#   If neither is set, the default db.sqlite3 in the project folder is used.

def _resolve_db_path():
    # 1. Environment variable (highest priority)
    env_path = os.environ.get('PATHLAB_DB_PATH', '').strip()
    if env_path:
        return Path(env_path)
    # 2. db_path.txt file in project root
    txt_file = BASE_DIR / 'db_path.txt'
    if txt_file.exists():
        line = txt_file.read_text(encoding='utf-8').strip().splitlines()
        if line and line[0].strip():
            return Path(line[0].strip())
    # 3. Default — local db.sqlite3
    return BASE_DIR / 'db.sqlite3'

def _resolve_media_path():
    env_path = os.environ.get('PATHLAB_MEDIA_PATH', '').strip()
    if env_path:
        return Path(env_path)
    txt_file = BASE_DIR / 'db_path.txt'
    if txt_file.exists():
        lines = txt_file.read_text(encoding='utf-8').strip().splitlines()
        if len(lines) >= 2 and lines[1].strip():
            return Path(lines[1].strip())
    return BASE_DIR / 'media'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _resolve_db_path(),
    }
}

# -- Internationalization ------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'   # IST (+5:30)
USE_I18N      = True
USE_TZ        = True

# -- Static & Media Files ------------------------------------------------------
STATIC_URL       = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT      = BASE_DIR / 'staticfiles'  # Run collectstatic for production

MEDIA_URL  = '/media/'
MEDIA_ROOT = _resolve_media_path()   # Uploads: logos, signatures, letterheads

# -- Authentication ------------------------------------------------------------
DEFAULT_AUTO_FIELD      = 'django.db.models.BigAutoField'
LOGIN_URL               = '/login/'
LOGIN_REDIRECT_URL      = '/dashboard/'
LOGOUT_REDIRECT_URL     = '/login/'
SESSION_COOKIE_AGE      = 86400  # 24 hours in seconds
MESSAGE_STORAGE         = 'django.contrib.messages.storage.session.SessionStorage'

# -- Pro Suite PIN Protection --------------------------------------------------
# These routes require an additional PIN before access.
# PIN is set in LabSettings model (pro_suite_password field).
PRO_SUITE_PIN  = 'Jatin123'
PRO_SUITE_URLS = [
    '/payments/', '/insurance/', '/notifications/', '/branches/',
    '/analyser/', '/hl7/', '/revenue/', '/expenditures/',
    '/inventory/', '/qc-log/', '/critical-alerts/', '/commissions/',
    '/home-collections/', '/settings/', '/staff/',
]

# -- Application Version -------------------------------------------------------
# Injected into all templates via context_processors.lab_context as APP_VERSION
APP_VERSION      = '1.1'
APP_VERSION_NAME = 'PathLab v1.1'
APP_BUILD_DATE   = '2026-04-09'
