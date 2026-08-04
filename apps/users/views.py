# apps/users/views.py
import logging

from urllib.parse import urlparse

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from apps.users.services import UserService
from apps.bookings.models import Booking
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.common.rate_limit import rate_limit
from apps.common.exceptions import ServiceError

logger = logging.getLogger("apps.users")


# ── REGISTER ──────────────────────────────────
@rate_limit("register", max_requests=5, window=300)
def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not email or not password1:
            messages.error(request, "Email and password are required.")
            return render(request, "users/register.html", {
                "form_data": {"email": email, "first_name": first_name, "last_name": last_name},
            })

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "users/register.html", {
                "form_data": {"email": email, "first_name": first_name, "last_name": last_name},
            })

        try:
            user = UserService.register(email, password1, first_name, last_name)
            login(request, user)
            messages.success(request, f"Welcome to CONSOLEX, {first_name or email}!")
            return redirect("home")
        except ServiceError as e:
            messages.error(request, str(e))
            return render(request, "users/register.html", {
                "form_data": {"email": email, "first_name": first_name, "last_name": last_name},
            })

    return render(request, "users/register.html")


# ── LOGIN ─────────────────────────────────────
@rate_limit("login", max_requests=5, window=60)
def user_login(request):
    if request.user.is_authenticated:
        return redirect("users:dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        try:
            user = UserService.login(request, email, password)
            login(request, user)
            # "Remember me": keep the persistent session (SESSION_COOKIE_AGE);
            # otherwise expire on browser close.
            if request.POST.get("remember") != "on":
                request.session.set_expiry(0)
            next_url = request.GET.get("next", "users:dashboard")
            parsed = urlparse(next_url)
            if parsed.netloc or parsed.scheme:
                next_url = "users:dashboard"
            return redirect(next_url)
        except ServiceError:
            messages.error(request, "Invalid email or password.")
            return render(request, "users/login.html", {
                "form_data": {"email": email},
            })

    return render(request, "users/login.html")


# ── LOGOUT ────────────────────────────────────
@require_POST
@login_required
def user_logout(request):
    logout(request)
    return redirect("home")


# ── DASHBOARD ─────────────────────────────────
@login_required
def user_dashboard(request):
    data = UserService.get_dashboard_data(request.user)

    # Pagination for the booking table
    paginator = Paginator(data["bookings"], 8)
    page_obj = paginator.get_page(request.GET.get("page"))
    data["page_obj"] = page_obj

    return render(request, "users/dashboard.html", data)


# ── PORTAL: PROFILE ───────────────────────────
@login_required
def user_profile(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()

        from django.core.exceptions import ValidationError as DjangoValidationError
        if phone:
            try:
                request.user._meta.get_field("phone").run_validators(phone)
            except DjangoValidationError as e:
                messages.error(request, " ".join(e.messages))
                return render(request, "users/profile.html", {
                    "unread_notifications_count": NotificationService.unread_count(request.user),
                })

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.phone = phone or None
        request.user.save(update_fields=["first_name", "last_name", "phone"])
        messages.success(request, "Profile updated successfully.")
        return redirect("users:profile")

    return render(request, "users/profile.html", {
        "unread_notifications_count": NotificationService.unread_count(request.user),
    })


# ── PORTAL: SETTINGS (password change) ────────
@login_required
def user_settings(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password", "")
        new_password1 = request.POST.get("new_password1", "")
        new_password2 = request.POST.get("new_password2", "")

        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        if not request.user.check_password(old_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
        else:
            try:
                validate_password(new_password1, user=request.user)
            except DjangoValidationError as e:
                messages.error(request, " ".join(e.messages))
            else:
                request.user.set_password(new_password1)
                request.user.save(update_fields=["password"])
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully.")
                return redirect("users:settings")

    return render(request, "users/settings.html", {
        "unread_notifications_count": NotificationService.unread_count(request.user),
    })


# ── PORTAL: NOTIFICATIONS ─────────────────────
@login_required
def user_notifications(request):
    notifications = (
        Notification.objects
        .filter(user=request.user)
        .order_by("-created_at")
    )
    paginator = Paginator(notifications, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "users/notifications.html", {
        "page_obj": page_obj,
        "unread_notifications_count": NotificationService.unread_count(request.user),
    })


@login_required
@require_POST
def notification_read_all(request):
    Notification.objects.mark_all_read(request.user)
    return redirect("users:notifications")


@login_required
@require_POST
def notification_read(request, notification_id):
    try:
        NotificationService.mark_read(request.user, notification_id)
    except ServiceError:
        messages.error(request, "Notification not found.")
    return redirect("users:notifications")


# ── PORTAL: MY BOOKINGS ───────────────────────
@login_required
def user_bookings(request):
    bookings = (
        Booking.objects
        .for_user(request.user)
        .order_by("-booking_date", "-start_time")
    )
    paginator = Paginator(bookings, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "users/bookings.html", {
        "page_obj": page_obj,
        "unread_notifications_count": NotificationService.unread_count(request.user),
    })
