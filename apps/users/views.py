from collections import Counter

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
        return redirect('users:dashboard')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=email, password=password)

        if user:
            login(request, user)
            next_url = request.GET.get('next', 'users:dashboard')
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

    # ── Booking stats ──────────────────────────
    total_bookings     = bookings.count()
    confirmed_bookings = bookings.filter(status='confirmed').count()
    pending_bookings   = bookings.filter(status='pending').count()
    completed_bookings = bookings.filter(status='completed').count()
    cancelled_bookings = bookings.filter(status='cancelled').count()

    total_spent = sum(
        b.payment.amount_rupees
        for b in bookings
        if hasattr(b, 'payment') and b.payment.status in ('captured', 'demo')
    )

    # ── Gaming progress ────────────────────────
    total_hours_played = sum(
        b.duration_hours for b in bookings if b.status == 'completed'
    )

    console_counter = Counter(
        b.game_console.name
        for b in bookings
        if b.game_console_id and b.status != 'cancelled'
    )
    favorite_console = console_counter.most_common(1)[0][0] if console_counter else None
    games_played      = len(console_counter)

    # ── Notifications ──────────────────────────
    notifications = request.user.notifications.order_by('-created_at')[:8]
    unread_notifications_count = request.user.notifications.filter(is_read=False).count()

    # ── Recent activity timeline (derived, no new models) ──
    activity = []
    for b in bookings[:8]:
        activity.append({
            'icon': '🎮',
            'text': f"Booked {b.game_console.name if b.game_console else 'a console'}",
            'timestamp': b.created_at,
        })
        if hasattr(b, 'payment') and b.payment.status in ('captured', 'demo'):
            activity.append({
                'icon': '💳',
                'text': f"Payment completed for Booking #{b.id}",
                'timestamp': b.payment.updated_at,
            })
        if b.status == 'cancelled':
            activity.append({
                'icon': '✖',
                'text': f"Booking #{b.id} cancelled",
                'timestamp': b.updated_at,
            })
    activity.sort(key=lambda a: a['timestamp'], reverse=True)
    activity = activity[:6]

    # ── Achievements (computed, not stored) ────
    achievements = [
        {
            'label': 'First Booking',
            'icon': '🕹️',
            'achieved': total_bookings >= 1,
        },
        {
            'label': 'Regular Player',
            'icon': '⭐',
            'achieved': total_bookings >= 5,
        },
        {
            'label': 'Marathon Gamer',
            'icon': '⏱️',
            'achieved': total_hours_played >= 20,
        },
        {
            'label': 'Big Spender',
            'icon': '💎',
            'achieved': total_spent >= 5000,
        },
    ]

    # ── Progress bar percentages (clamped 0–100) ──
    hours_progress_pct = min(round((total_hours_played / 40) * 100), 100) if total_hours_played else 0
    games_progress_pct = min(round((games_played / 10) * 100), 100) if games_played else 0

    context = {
        'bookings':                   bookings,
        'total_bookings':             total_bookings,
        'confirmed_bookings':         confirmed_bookings,
        'pending_bookings':           pending_bookings,
        'completed_bookings':         completed_bookings,
        'cancelled_bookings':         cancelled_bookings,
        'total_spent':                total_spent,
        'total_hours_played':         round(total_hours_played, 1),
        'favorite_console':           favorite_console,
        'games_played':               games_played,
        'notifications':              notifications,
        'unread_notifications_count': unread_notifications_count,
        'activity':                   activity,
        'achievements':               achievements,
        'hours_progress_pct':         hours_progress_pct,
        'games_progress_pct':         games_progress_pct,
    }
    return render(request, 'users/dashboard.html', context)