# apps/bookings/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
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

            if not console_id:
                messages.error(request, "Please select a PS5 setup.")
                return render(request, 'bookings/booking_form.html',
                               {'consoles': consoles, 'rate_table': rate_table})

            console = get_object_or_404(GameConsole, id=console_id)

            # Parse inputs safely
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()

            # Reject past dates — a booking must be in the future.
            if booking_date < datetime.now().date():
                messages.error(request, "Please choose a future date.")
                return render(request, 'bookings/booking_form.html',
                               {'consoles': consoles, 'rate_table': rate_table})

            # Calculate end time
            start_datetime = datetime.combine(booking_date, start_time)
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            end_time = end_datetime.time()

            # Slot Conflict Detection — serialized to avoid a race.
            # We lock the console row (select_for_update) so two concurrent
            # bookings for the same console cannot both pass the overlap
            # check and double-book the slot. The conflict check also scopes
            # by console when one is selected.
            with transaction.atomic():
                if console is not None:
                    # Lock the console row; releases at end of the block.
                    GameConsole.objects.select_for_update().get(pk=console.pk)

                conflict_filter = Q(booking_date=booking_date) & Q(
                    status__in=['pending', 'confirmed']
                ) & Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
                if console is not None:
                    conflict_filter &= Q(game_console=console)

                conflicting_bookings = Booking.objects.filter(conflict_filter)

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

                # Create Booking (inside the locked block, so the overlap
                # check and insert are atomic for this console).
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