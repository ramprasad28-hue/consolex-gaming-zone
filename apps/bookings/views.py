# apps/bookings/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Booking
from apps.games.models import GameConsole
from .pricing import (
    calculate_total,
    apply_membership_discount,
    RATE_PER_PLAYER_HOUR,
)


@login_required
def booking_form(request):
    consoles = GameConsole.objects.filter(is_active=True)

    # Rate table exposed to the template for the live cost preview.
    rate_table = {str(k): float(v) for k, v in RATE_PER_PLAYER_HOUR.items()}

    if request.method == 'POST':
        try:
            booking_date_str = request.POST.get('booking_date')
            start_time_str = request.POST.get('start_time')
            duration_hours = int(request.POST.get('duration_hours'))
            number_of_players = int(request.POST.get('number_of_players'))
            console_id = request.POST.get('game_console')

            if number_of_players not in RATE_PER_PLAYER_HOUR:
                messages.error(request, "Invalid number of players selected.")
                return render(request, 'bookings/booking_form.html',
                               {'consoles': consoles, 'rate_table': rate_table})

            console = get_object_or_404(GameConsole, id=console_id) if console_id else None

            # Parse inputs safely
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()

            # Calculate end time
            start_datetime = datetime.combine(booking_date, start_time)
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            end_time = end_datetime.time()

            # Slot Conflict Detection
            # Check for any booking that overlaps with the requested time on the same date
            # Overlap condition: ExistingStart < RequestedEnd AND RequestedStart < ExistingEnd
            conflicting_bookings = Booking.objects.filter(
                booking_date=booking_date,
                status__in=['pending', 'confirmed']
            ).filter(
                Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
            )

            if conflicting_bookings.exists():
                messages.error(request, "This time slot is already booked. Please choose a different time.")
                return render(request, 'bookings/booking_form.html',
                               {'consoles': consoles, 'rate_table': rate_table})

            # Calculate Total Cost from the console rate (weekday/weekend) x
            # player multiplier x duration, then apply membership discount.
            total_cost = calculate_total(
                console, booking_date, duration_hours, number_of_players
            )

            active_membership = (
                request.user.membership
                if getattr(request.user, 'membership', None) else None
            )
            if active_membership:
                total_cost = apply_membership_discount(
                    total_cost, active_membership.discount_percent
                )

            # Create Booking
            booking = Booking.objects.create(
                user=request.user,
                game_console=console,
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time,
                number_of_players=number_of_players,
                total_cost=total_cost,
                status='pending'
            )

            messages.success(request, "Slot available! Proceed to pay the 30% advance.")
            return redirect('payments:payment_page', booking_id=booking.id)

        except (ValueError, KeyError) as e:
            messages.error(request, f"Invalid form data submitted. Please check your inputs. {str(e)}")
            return render(request, 'bookings/booking_form.html',
                           {'consoles': consoles, 'rate_table': rate_table})

    return render(request, 'bookings/booking_form.html',
                   {'consoles': consoles, 'rate_table': rate_table})

@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'bookings/booking_detail.html', {'booking': booking})