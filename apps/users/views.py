from urllib.parse import urlparse

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from apps.bookings.models import Booking
from apps.common.rate_limit import rate_limit


# ── REGISTER ──────────────────────────────────
@rate_limit("register", max_requests=5, window=300)
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

        # Enforce Django's AUTH_PASSWORD_VALIDATORS (minimum length,
        # common password, numeric-only, similarity checks).
        try:
            validate_password(password1)
        except ValidationError as e:
            for err in e.messages:
                messages.error(request, err)
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
@rate_limit("login", max_requests=5, window=60)
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
            # Prevent open-redirect attacks: only allow relative paths
            # on the same host (no scheme or double-slash).
            parsed = urlparse(next_url)
            if parsed.netloc or parsed.scheme:
                next_url = 'users:dashboard'
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'users/login.html')


# ── LOGOUT ────────────────────────────────────
@require_POST
@login_required
def user_logout(request):
    logout(request)
    return redirect('home')


# ── DASHBOARD ─────────────────────────────────
@login_required
def user_dashboard(request):
    all_bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('game_console', 'payment')
        .order_by('-booking_date', '-start_time')
    )

    # Paginate the booking table (8 per page) so heavy users stay fast.
    paginator = Paginator(all_bookings, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    bookings = all_bookings  # kept for derived stats/activity below

    # ── Booking stats (single query with annotations) ──
    from django.db.models import Sum, Count, Q, F
    stats = all_bookings.aggregate(
        total=Count('id'),
        confirmed=Count('id', filter=Q(status='confirmed')),
        pending=Count('id', filter=Q(status='pending')),
        completed=Count('id', filter=Q(status='completed')),
        cancelled=Count('id', filter=Q(status='cancelled')),
    )
    total_bookings     = stats['total']
    confirmed_bookings = stats['confirmed']
    pending_bookings   = stats['pending']
    completed_bookings = stats['completed']
    cancelled_bookings = stats['cancelled']

    from decimal import Decimal
    total_spent = all_bookings.filter(
        payment__status__in=['captured', 'demo']
    ).aggregate(
        total=Sum('payment__amount')
    )['total'] or 0
    total_spent = (Decimal(total_spent) / Decimal(100)).quantize(Decimal('0.01'))

    # ── Gaming progress ────────────────────────
    completed = all_bookings.filter(status='completed')
    total_hours_played = sum(b.duration_hours for b in completed[:200])

    console_stats = (
        all_bookings
        .filter(status__in=['confirmed', 'completed', 'pending'])
        .values('game_console__name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
    )
    console_list = [(c['game_console__name'], c['cnt']) for c in console_stats if c['game_console__name']]
    favorite_console = console_list[0][0] if console_list else None
    games_played = len(console_list)

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
        'page_obj':                   page_obj,
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