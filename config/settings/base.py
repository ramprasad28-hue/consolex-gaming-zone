from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY has no default in production — it must be supplied via env.
# A dev-only fallback is provided so local runs work without a .env file.
import os as _os
SECRET_KEY = _os.environ.get('SECRET_KEY') or config('SECRET_KEY', default='dev-only-insecure-key-change-me')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.users',
    'apps.bookings',
    'apps.games',
    'apps.payments',
    'apps.dashboard',
    'apps.memberships',
    'apps.notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR.parent / 'static']
STATIC_ROOT = BASE_DIR.parent / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR.parent / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'   # will enable after Phase 2

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/users/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ─────────────────────────────────────────────
# Third-party credentials — ALL loaded from environment.
# Never hardcode secrets here. They are read from .env (dev) or the
# platform's env vars (prod). Empty strings are safe fallbacks so the
# app still boots locally; payment/WhatsApp features simply no-op until
# real keys are provided.
# ─────────────────────────────────────────────

# Razorpay
RAZORPAY_KEY_ID        = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET    = config('RAZORPAY_KEY_SECRET', default='')
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default='')

# Twilio WhatsApp
TWILIO_ACCOUNT_SID   = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN    = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_WHATSAPP_FROM = config('TWILIO_WHATSAPP_FROM', default='')
OWNER_WHATSAPP_TO    = config('OWNER_WHATSAPP_TO', default='')