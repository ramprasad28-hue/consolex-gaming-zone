from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

from apps.memberships.models import Membership
from apps.tournaments.models import Tournament
from apps.games.models import Game


def home(request):
    plans = Membership.objects.filter(is_active=True)
    tournaments = Tournament.objects.filter(is_active=True).order_by("date")[:6]
    games = Game.objects.filter(is_active=True).order_by("sort_order", "title")[:12]
    return render(request, "pages/home.html", {
        "plans": plans,
        "tournaments": tournaments,
        "games": games,
    })


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