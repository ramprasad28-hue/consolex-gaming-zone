from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render


def home(request):
    return render(request, "pages/home.html")


urlpatterns = [
    path("admin/", admin.site.urls),

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