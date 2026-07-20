from django.urls import path
from . import views

app_name = "memberships"

urlpatterns = [
    path("", views.plan_list, name="plan_list"),
    path("<int:plan_id>/subscribe/", views.subscribe, name="subscribe"),
]
