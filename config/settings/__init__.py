
import os

from django.core.exceptions import ImproperlyConfigured

env = os.environ.get('DJANGO_ENV', 'development')

if env == 'production':
    from .production import *
elif env == 'development':
    from .development import *
else:
    raise ImproperlyConfigured(
        f"DJANGO_ENV={env!r} is not a valid value. Use 'development' or 'production'."
    )
