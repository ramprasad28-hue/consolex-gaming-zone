from .base import *
import os

DEBUG = False

# Add your platform subdomain here once you deploy
# e.g. 'consolex.up.railway.app' or 'consolex.onrender.com'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

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