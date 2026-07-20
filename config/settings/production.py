from .base import *
import os

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ── Security headers ─────────────────────────
SECURE_BROWSER_XSS_FILTER        = True
SECURE_CONTENT_TYPE_NOSNIFF      = True
X_FRAME_OPTIONS                  = 'DENY'
SECURE_REFERRER_POLICY           = 'same-origin'

# Enable these once you have HTTPS working:
# SECURE_SSL_REDIRECT            = True
# SESSION_COOKIE_SECURE          = True
# CSRF_COOKIE_SECURE             = True
# SECURE_HSTS_SECONDS            = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Email (configure with real SMTP when ready)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'