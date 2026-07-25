from django.urls import path
from . import notification_views

urlpatterns = [
    path("", notification_views.notification_list, name="api-notification-list"),
    path("<int:pk>/read/", notification_views.mark_read, name="api-notification-mark-read"),
]
