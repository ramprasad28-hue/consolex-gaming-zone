from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.core.views import home

admin.site.site_header = "CONSOLEX Admin"
admin.site.site_title = "CONSOLEX"
admin.site.index_title = "Management"


urlpatterns = [
    path("admin/", admin.site.urls),

    # API
    path("api/", include("apps.api.urls")),

    # Homepage
    path("", home, name="home"),

    # Users
    path("users/", include("apps.users.urls")),

    # Bookings
    path("bookings/", include("apps.bookings.urls")),

    # Payments
    path("payments/", include("apps.payments.urls")),

    # Memberships
    path("memberships/", include("apps.memberships.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)