from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("dashboard/", views.user_dashboard, name="dashboard"),

    # Player portal (Ch11)
    path("profile/", views.user_profile, name="profile"),
    path("settings/", views.user_settings, name="settings"),
    path("notifications/", views.user_notifications, name="notifications"),
    path("notifications/read-all/", views.notification_read_all, name="notifications_read_all"),
    path("notifications/<int:notification_id>/read/", views.notification_read, name="notification_read"),
    path("bookings/", views.user_bookings, name="bookings"),

    # Password reset (Django built-ins)
    path("password-reset/",
         auth_views.PasswordResetView.as_view(
             template_name="users/password_reset.html",
             email_template_name="users/password_reset_email.html",
             success_url="/users/password-reset/done/"),
         name="password_reset"),
    path("password-reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="users/password_reset_done.html"),
         name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="users/password_reset_confirm.html",
             success_url="/users/password-reset/complete/"),
         name="password_reset_confirm"),
    path("password-reset/complete/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="users/password_reset_complete.html"),
         name="password_reset_complete"),
]