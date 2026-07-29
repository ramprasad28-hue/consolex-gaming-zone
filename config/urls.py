from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

from apps.core.views import home

admin.site.site_header = "CONSOLEX Admin"
admin.site.site_title = "CONSOLEX"
admin.site.index_title = "Management"


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler403(request, exception):
    return render(request, '403.html', status=403)


def handler500(request):
    return render(request, '500.html', status=500)


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

    # Games
    path("games/", include("apps.games.urls")),

    # Tournaments
    path("tournaments/", include("apps.tournaments.urls")),

    # Staff Portal
    path("staff/", include("apps.staff.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)