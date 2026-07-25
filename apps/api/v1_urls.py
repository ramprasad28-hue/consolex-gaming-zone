"""
API v1 URL configuration.

All v1 endpoints are namespaced under api/v1/ for forward compatibility.
"""
from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.api.auth_urls")),
    path("bookings/", include("apps.api.booking_urls")),
    path("payments/", include("apps.api.payment_urls")),
    path("memberships/", include("apps.api.membership_urls")),
    path("consoles/", include("apps.api.console_urls")),
    path("dashboard/", include("apps.api.dashboard_urls")),
    path("notifications/", include("apps.api.notification_urls")),
]
