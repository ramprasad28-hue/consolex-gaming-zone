# ─────────────────────────────────────────────
# File: apps/bookings/views.py
# ─────────────────────────────────────────────

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Booking
from apps.games.models import GameConsole


# ── HOURLY RATES ─────────────────────────────
RATE_PER_HOUR = {
    1: 300,   # 1 player
    2: 500,   # 2 players
    3: 700,
    4: 900,
}
DEFAULT_RATE = 300


def calculate_cost(start_time, end_time, players):
    """Pure function — calculate total cost from times and player count."""
    from datetime import datetime, date
    start    = datetime.combine(date.today(), start_time)
    end      = datetime.combine(date.today(), end_time)
    hours    = max((end - start).seconds / 3600, 0)
    rate     = RATE_PER_HOUR.get(players, DEFAULT_RATE)
    return round(hours * rate, 2)


def has_conflict(booking_date, start_time, end_time, game_console, exclude_id=None):
    """Returns True if another booking overlaps this slot."""
    qs = Booking.objects.filter(
        booking_date  = booking_date,
        game_console  = game_console,
        status__in    = ['pending', 'confirmed'],
        start_time__lt = end_time,
        end_time__gt   = start_time,
    )
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()


# ── BOOKING FORM ──────────────────────────────
@login_required
def booking_form(request):
    consoles = GameConsole.objects.filter(is_available=True)

    if request.method == 'POST':
        # Pull form data
        game_console_id = request.POST.get('game_console')
        booking_date    = request.POST.get('booking_date')
        start_time      = request.POST.get('start_time')
        end_time        = request.POST.get('end_time')
        players_raw     = request.POST.get('number_of_players', 1)

        # Basic validation
        if not all([game_console_id, booking_date, start_time, end_time]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'bookings/booking_form.html', {'consoles': consoles})

        try:
            from datetime import datetime, time as dt_time, date as dt_date
            players     = int(players_raw)
            b_date      = datetime.strptime(booking_date, '%Y-%m-%d').date()
            b_start     = datetime.strptime(start_time,   '%H:%M').time()
            b_end       = datetime.strptime(end_time,     '%H:%M').time()
            game_console = GameConsole.objects.get(id=game_console_id)
        except Exception:
            messages.error(request, 'Invalid booking details. Please try again.')
            return render(request, 'bookings/booking_form.html', {'consoles': consoles})

        # Past date check
        if b_date < timezone.localdate():
            messages.error(request, 'Booking date cannot be in the past.')
            return render(request, 'bookings/booking_form.html', {'consoles': consoles})

        # Time logic check
        if b_end <= b_start:
            messages.error(request, 'End time must be after start time.')
            return render(request, 'bookings/booking_form.html', {'consoles': consoles})

        # Conflict detection
        if has_conflict(b_date, b_start, b_end, game_console):
            messages.error(
                request,
                'This slot is already booked. Please choose a different time.'
            )
            return render(request, 'bookings/booking_form.html', {'consoles': consoles})

        # Calculate and store cost
        total = calculate_cost(b_start, b_end, players)

        booking = Booking.objects.create(
            user              = request.user,
            game_console      = game_console,
            booking_date      = b_date,
            start_time        = b_start,
            end_time          = b_end,
            number_of_players = players,
            total_cost        = total,
            status            = 'pending',
        )

        messages.success(request, 'Slot reserved! Complete payment to confirm.')
        return redirect('payment_page', booking_id=booking.id)

    return render(request, 'bookings/booking_form.html', {'consoles': consoles})


# ── BOOKING DETAIL ────────────────────────────
@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'bookings/booking_detail.html', {'booking': booking})