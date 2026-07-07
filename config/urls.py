# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.users.urls')), # Handles root, login, register, dashboard
    path('bookings/', include('apps.bookings.urls')),
    path('payments/', include('apps.payments.urls')),
]

# Serve static files in development/demo if needed
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)