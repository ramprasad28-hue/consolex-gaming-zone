from django.urls import path
from . import auth_views

urlpatterns = [
    path("register/", auth_views.register, name="api-register"),
    path("login/", auth_views.login_view, name="api-login"),
    path("logout/", auth_views.logout_view, name="api-logout"),
    path("me/", auth_views.me, name="api-me"),
]
