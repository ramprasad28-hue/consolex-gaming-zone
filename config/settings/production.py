from .base import *
import os
import urllib.parse as _urlparse

DEBUG = False

# SECRET_KEY MUST be provided via environment in production.
# No insecure fallback — fail fast if it is missing or still the dev default.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY or SECRET_KEY == 'dev-only-insecure-key-change-me':
    raise RuntimeError(
        "SECRET_KEY environment variable is required and must not be the "
        "dev default. Set it in your hosting provider's env config."
    )

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not any(h.strip() for h in ALLOWED_HOSTS):
    raise RuntimeError(
        "ALLOWED_HOSTS environment variable is required in production."
    )

# ── Database — PostgreSQL required for production ────────────
# DATABASE_URL is the provider-standard connection string used by Railway,
# Render, Heroku and most managed Postgres add-ons:
#   postgres://<user>:<password>@<host>:<port>/<name>
# It takes precedence when set. If absent, the discrete DB_* variables (with
# DB_HOST explicitly required) are used as a deliberate fallback. If neither
# is provided we fail fast — production must never silently dial localhost.
# Parsed with the stdlib so no dj-database-url dependency is required.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
    }
}

_database_url = (os.environ.get('DATABASE_URL') or '').strip()
if _database_url:
    _parsed = _urlparse.urlparse(_database_url)
    _scheme = _parsed.scheme.lower()
    if _scheme not in ('postgres', 'postgresql'):
        raise RuntimeError(
            "DATABASE_URL in production must be postgres:// or "
            "postgresql:// (got {}://).".format(_scheme)
        )
    if not _parsed.hostname:
        raise RuntimeError("DATABASE_URL is missing a hostname.")
    DATABASES['default'].update({
        'NAME': _urlparse.unquote(_parsed.path.lstrip('/')) or 'consolex',
        'USER': _urlparse.unquote(_parsed.username or ''),
        'PASSWORD': _urlparse.unquote(_parsed.password or ''),
        'HOST': _parsed.hostname,
        'PORT': str(_parsed.port or 5432),
    })
    _sslmode = dict(_urlparse.parse_qsl(_parsed.query)).get('sslmode')
    if _sslmode:
        DATABASES['default']['OPTIONS'] = {'sslmode': _sslmode}
elif os.environ.get('DB_HOST'):
    _db_host = os.environ.get('DB_HOST').strip()
    if not _db_host:
        raise RuntimeError(
            "DB_HOST must not be empty when it is provided in production."
        )
    DATABASES['default'].update({
        'NAME': os.environ.get('DB_NAME', 'consolex'),
        'USER': os.environ.get('DB_USER', 'consolex'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': _db_host,
        'PORT': os.environ.get('DB_PORT', '5432'),
    })
else:
    raise RuntimeError(
        "DATABASE_URL or DB_HOST must be provided in production. "
        "Refusing to silently fall back to localhost."
    )

# ── Cache — shared Redis across all Gunicorn workers ─────────
# LocMemCache (base.py) is process-local: rate limits and CMS cache
# invalidation break under multiple workers. Redis is required in prod.
# Credentials live inside REDIS_URL only (e.g. redis://host:6379/0 or a
# provider URL such as rediss://default:<password>@<host>:<port>).
REDIS_URL = os.environ.get('REDIS_URL')
if not REDIS_URL:
    raise RuntimeError(
        "REDIS_URL environment variable is required in production so all "
        "workers share one cache (rate limiting, DRF throttles, CMS cache)."
    )

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'KEY_PREFIX': 'consolex',
    }
}

# ── CORS — production allows only explicitly configured origins. ─
# base.py seeds dev-only localhost origins for the local server; those
# must not apply to production traffic.
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if o.strip()
]

# ── Security headers ─────────────────────────
# NOTE: SECURE_BROWSER_XSS_FILTER was previously set here; it is a no-op in
# Django 6 (the header/setting was removed) so it is intentionally absent.
SECURE_CONTENT_TYPE_NOSNIFF      = True
X_FRAME_OPTIONS                  = 'DENY'
SECURE_REFERRER_POLICY           = 'same-origin'

# HTTPS / HSTS — the platform (Railway, Render, Nginx, Cloudflare, …) is
# expected to terminate TLS and forward X-Forwarded-Proto. Both values are
# env-controllable so platforms with different proxy setups can adapt.
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'true').lower() == 'true'

_proxy_header = os.environ.get('DJANGO_SECURE_PROXY_SSL_HEADER', 'HTTP_X_FORWARDED_PROTO:https').strip()
if _proxy_header:
    _name, _sep, _value = _proxy_header.partition(':')
    SECURE_PROXY_SSL_HEADER = (_name.strip().upper(), _value.strip())
else:
    SECURE_PROXY_SSL_HEADER = None

SESSION_COOKIE_SECURE            = True
CSRF_COOKIE_SECURE               = True
SECURE_HSTS_SECONDS              = int(os.environ.get('DJANGO_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS   = True
# HSTS preload registration submits the domain to browsers' preload lists
# globally — keep OFF unless you intentionally applied via hstspreload.org.
SECURE_HSTS_PRELOAD              = os.environ.get('DJANGO_HSTS_PRELOAD', 'false').lower() == 'true'

SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# Session
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE              = 86400  # 24 hours

# ── Email — configure with real SMTP when ready ──────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST     = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT     = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS  = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = os.environ.get('DEFAULT_FROM_EMAIL', 'CONSOLEX <noreply@consolex.in>')