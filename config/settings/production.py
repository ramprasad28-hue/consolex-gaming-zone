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

# ── Database — PostgreSQL required for production ────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'consolex'),
        'USER': os.environ.get('DB_USER', 'consolex'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# ── Security headers ─────────────────────────
SECURE_BROWSER_XSS_FILTER        = True
SECURE_CONTENT_TYPE_NOSNIFF      = True
X_FRAME_OPTIONS                  = 'DENY'
SECURE_REFERRER_POLICY           = 'same-origin'

# HTTPS / HSTS — enable once SSL is working (Railway, Render, Nginx, etc.)
SECURE_SSL_REDIRECT              = True
SESSION_COOKIE_SECURE            = True
CSRF_COOKIE_SECURE               = True
SECURE_HSTS_SECONDS              = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS   = True
SECURE_HSTS_PRELOAD              = True

# If behind a reverse proxy (Railway, Render, Cloudflare, etc.)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
