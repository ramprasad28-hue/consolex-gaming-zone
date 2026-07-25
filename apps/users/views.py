# apps/users/views.py
import logging

from urllib.parse import urlparse

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from apps.users.services import UserService
from apps.bookings.models import Booking
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
            return render(request, "users/register.html")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "users/register.html")

        try:
            user = UserService.register(email, password1, first_name, last_name)
            login(request, user)
            messages.success(request, f"Welcome to CONSOLEX, {first_name or email}!")
            return redirect("home")
        except ServiceError as e:
            messages.error(request, str(e))
            return render(request, "users/register.html")

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
            next_url = request.GET.get("next", "users:dashboard")
            parsed = urlparse(next_url)
            if parsed.netloc or parsed.scheme:
                next_url = "users:dashboard"
            return redirect(next_url)
        except ServiceError:
            messages.error(request, "Invalid email or password.")

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
