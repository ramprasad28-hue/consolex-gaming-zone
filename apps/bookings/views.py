from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .forms import BookingForm
from .models import Booking

WEEKDAY_RATES = {1: 130, 2: 250, 3: 330, 4: 420}
WEEKEND_RATES = {1: 150, 2: 280, 3: 370, 4: 460}

def calculate_cost(console, date, duration_hours, players):
    is_weekend = date.weekday() >= 5  # Saturday=5, Sunday=6
    rates = WEEKEND_RATES if is_weekend else WEEKDAY_RATES
    hourly = rates.get(players, 130)
    return Decimal(hourly * duration_hours)


@login_required
def booking_create(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            console   = d['console']
            date      = d['date']
            duration  = int(d['duration'])
            players   = int(d['number_of_players'])
            h, m      = map(int, d['start_time'].split(':'))
            from datetime import time
            start_time = time(h, m)
            end_time   = d['end_time']
            total_cost = calculate_cost(console, date, duration, players)

            booking = Booking.objects.create(
                user=request.user,
                console=console,
                date=date,
                start_time=start_time,
                end_time=end_time,
                number_of_players=players,
                total_cost=total_cost,
                status='pending',
            )
            messages.success(request, 'Booking created! Please complete your advance payment.')
            return redirect('booking_payment', pk=booking.pk)
    else:
        form = BookingForm()
    return render(request, 'bookings/booking_form.html', {'form': form})


@login_required
def booking_payment(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    advance = (booking.total_cost * Decimal('0.3')).quantize(Decimal('1'))
    return render(request, 'bookings/booking_payment.html', {
        'booking': booking,
        'advance': advance,
    })


@login_required
def booking_confirm(request, pk):
    """Called after Razorpay success webhook / manual confirm for now."""
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    booking.status = 'confirmed'
    booking.save()

    # Send owner notification
    from apps.notifications.models import Notification
    Notification.objects.create(
        user=request.user,
        message=(
            f"New booking confirmed!\n"
            f"Customer: {request.user.email}\n"
            f"Console: {booking.console.name}\n"
            f"Date: {booking.date} | {booking.start_time} – {booking.end_time}\n"
            f"Players: {booking.number_of_players}\n"
            f"Total: ₹{booking.total_cost}"
        )
    )
    messages.success(request, 'Your booking is confirmed!')
    return redirect('dashboard')
