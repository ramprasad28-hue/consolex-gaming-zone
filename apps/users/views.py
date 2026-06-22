from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.bookings.models import Booking


# ── REGISTER ──────────────────────────────────
def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()

        email      = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')

        if not email or not password1:
            messages.error(request, 'Email and password are required.')
            return render(request, 'users/register.html')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'users/register.html')

        user = User.objects.create_user(
            email      = email,
            password   = password1,
            first_name = first_name,
            last_name  = last_name,
        )
        login(request, user)
        messages.success(request, f'Welcome to CONSOLEX, {first_name or email}!')
        return redirect('home')

    return render(request, 'users/register.html')


# ── LOGIN ─────────────────────────────────────
def user_login(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=email, password=password)

        if user:
            login(request, user)
            next_url = request.GET.get('next', 'user_dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'users/login.html')


# ── LOGOUT ────────────────────────────────────
def user_logout(request):
    logout(request)
    return redirect('home')


# ── DASHBOARD ─────────────────────────────────
@login_required
def user_dashboard(request):
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('game_console', 'payment')
        .order_by('-booking_date', '-start_time')
    )

    # Booking stats
    total_bookings     = bookings.count()
    confirmed_bookings = bookings.filter(status='confirmed').count()
    pending_bookings   = bookings.filter(status='pending').count()
    total_spent        = sum(
        b.payment.amount_rupees
        for b in bookings
        if hasattr(b, 'payment') and b.payment.status in ('captured', 'demo')
    )

    context = {
        'bookings':           bookings,
        'total_bookings':     total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'pending_bookings':   pending_bookings,
        'total_spent':        total_spent,
    }
    return render(request, 'users/dashboard.html', context)