# apps/bookings/views.py
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.bookings.pricing import RATE_PER_PLAYER_HOUR
from apps.games.models import GameConsole
from apps.common.exceptions import ServiceError

logger = logging.getLogger("apps.bookings")


@login_required
def booking_form(request):
    consoles = GameConsole.objects.filter(is_active=True)
    rate_table = {str(k): float(v) for k, v in RATE_PER_PLAYER_HOUR.items()}

    if request.method == "POST":
        try:
            booking_date_str = request.POST.get("booking_date")
            start_time_str = request.POST.get("start_time")
            duration_hours = int(request.POST.get("duration_hours"))
            number_of_players = int(request.POST.get("number_of_players"))
            console_id = request.POST.get("game_console")

            from datetime import datetime
            booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M").time()

            booking = BookingService.create_booking(
                user=request.user,
                console_id=console_id,
                booking_date=booking_date,
                start_time=start_time,
                duration_hours=duration_hours,
                number_of_players=number_of_players,
            )

            messages.success(request, "Slot available! Proceed to pay the 30% advance.")
            return redirect("payments:payment_page", booking_id=booking.id)

        except (ServiceError, ValueError, KeyError) as e:
            msg = str(e) if isinstance(e, ServiceError) else "Invalid form data. Please check your inputs and try again."
            messages.error(request, msg)
            return render(request, "bookings/booking_form.html",
                          {"consoles": consoles, "rate_table": rate_table})

    return render(request, "bookings/booking_form.html",
                  {"consoles": consoles, "rate_table": rate_table})


@login_required
def booking_detail(request, booking_id):
    booking = BookingService.get_for_user(request.user, booking_id)
    return render(request, "bookings/booking_detail.html", {"booking": booking})


@login_required
def booking_cancel(request, booking_id):
    if request.method != "POST":
        return redirect("bookings:booking_detail", booking_id=booking_id)

    try:
        BookingService.cancel_booking(request.user, booking_id)
        messages.success(request, f"Booking #{booking_id} cancelled successfully.")
    except ServiceError as e:
        messages.error(request, str(e))

    return redirect("users:dashboard")
