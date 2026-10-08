import os
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'changeme-in-dev')

DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
    'axes',
    'django_prometheus',
    'core',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',  # last except the Prometheus timer, which must wrap everything
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # must be first: refuses locked-out logins
    'django.contrib.auth.backends.ModelBackend',
]

# Login lockout (django-axes) for every password check: login pages, admin, API token endpoint.
# Keyed on username + IP, so an attacker can't lock a user out everywhere.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_RESET_ON_SUCCESS = True
AXES_CLIENT_IP_CALLABLE = 'core.api_views.client_ip'  # same proxy-aware IP as API throttling

ROOT_URLCONF = 'trustsite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'trustsite.wsgi.application'

def database_from_url(url):
    """postgres://user:pass@host:port/name?sslmode=require -> Django DATABASES entry."""
    parts = urlsplit(url)
    if parts.scheme not in ('postgres', 'postgresql'):
        raise ImproperlyConfigured(f'DATABASE_URL must be a postgres:// URL, got {parts.scheme}://')
    return {
        'ENGINE': 'django_prometheus.db.backends.postgresql',  # postgresql + query metrics
        'NAME': unquote(parts.path.lstrip('/')),
        'USER': unquote(parts.username or ''),
        'PASSWORD': unquote(parts.password or ''),
        'HOST': parts.hostname or '',
        'PORT': str(parts.port or ''),
        'OPTIONS': dict(parse_qsl(parts.query)),
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }


# Postgres when DATABASE_URL is set (docker-compose, production); SQLite otherwise.
if os.environ.get('DATABASE_URL'):
    DATABASES = {'default': database_from_url(os.environ['DATABASE_URL'])}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django_prometheus.db.backends.sqlite3',
            'NAME': os.environ.get('DJANGO_DB_PATH', BASE_DIR / 'db.sqlite3'),
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

LOGIN_URL = 'rest_framework:login'
LOGIN_REDIRECT_URL = '/'

# Alerts (core/alerts.py): webhook and/or email; neither set = log only
ALERT_WEBHOOK_URL = os.environ.get('ALERT_WEBHOOK_URL', '')
ALERT_EMAILS = [e.strip() for e in os.environ.get('ALERT_EMAILS', '').split(',') if e.strip()]
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'alerts@trust-control-center.local')
if os.environ.get('EMAIL_HOST'):
    EMAIL_HOST = os.environ['EMAIL_HOST']
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') == '1'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery + Redis (optional). REDIS_URL set: tasks go to the worker and Redis is the shared cache
# (so rate limits count across gunicorn workers). Unset: tasks run inline, local-memory cache.
REDIS_URL = os.environ.get('REDIS_URL', '')
CELERY_BROKER_URL = REDIS_URL or 'memory://'
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = not REDIS_URL
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
if REDIS_URL and not TESTING:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': REDIS_URL}}

# Prometheus scrape token for /metrics; unset = endpoint disabled (404)
METRICS_TOKEN = os.environ.get('METRICS_TOKEN', '')

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
if not DEBUG:
    STORAGES = {
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # ?search=, ?ordering=, and exact filters from each viewset's filterset_fields
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Reads are public; writes need the matching Django model permission (Editor group or superuser)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # No BasicAuthentication: it checks passwords on every endpoint with no throttle
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    # Client IP for throttling. Unset, DRF trusts the whole client-supplied X-Forwarded-For,
    # so rotating it bypasses rate limits. Production sits behind one TLS proxy (see
    # SECURE_PROXY_SSL_HEADER); with no proxy (local / docker-compose) use REMOTE_ADDR.
    'NUM_PROXIES': int(os.environ.get('DJANGO_NUM_PROXIES', '0' if DEBUG else '1')),
    # ponytail: LocMemCache is per gunicorn worker, so the effective limit is rate x workers; use Redis cache if that matters
    # Per-client API rate limits (429 when exceeded). The suite makes many requests from one IP, so tests
    # get a high ceiling; throttle tests set their own rates.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100000/min' if TESTING else os.environ.get('API_RATE_ANON', '120/min'),
        'user': '100000/min' if TESTING else os.environ.get('API_RATE_USER', '600/min'),
        'token': '10/min',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Trust Control Center API',
    'DESCRIPTION': 'Cross-source metric reconciliation, trust scoring, and OSI export.',
    'VERSION': '1.0.0',
}

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8000'
).split(',')
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Security settings for production
if not DEBUG:
    # Hosts like Render/Heroku/Fly terminate TLS at a proxy. Without this, Django sees
    # http while the browser sends Origin: https://..., and every form POST fails CSRF.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
