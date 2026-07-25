from django.urls import path
from . import console_views

urlpatterns = [
    path("", console_views.console_list, name="api-console-list"),
    path("<int:pk>/", console_views.console_detail, name="api-console-detail"),
]
