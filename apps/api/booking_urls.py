from django.urls import path
from . import booking_views

urlpatterns = [
    path("", booking_views.booking_list, name="api-booking-list"),
    path("create/", booking_views.booking_create, name="api-booking-create"),
    path("<int:pk>/", booking_views.booking_detail, name="api-booking-detail"),
    path("<int:pk>/cancel/", booking_views.booking_cancel, name="api-booking-cancel"),
]
