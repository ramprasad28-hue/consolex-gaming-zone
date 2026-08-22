# apps/bookings/views.py
import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.bookings.forms import BookingCreateForm
from apps.bookings.pricing import RATE_PER_PLAYER_HOUR, RATE_PER_PLAYER_HOUR_WEEKEND
from apps.games.models import GameConsole
from apps.common.exceptions import ServiceError

logger = logging.getLogger("apps.bookings")


@login_required
def booking_form(request):
    consoles = GameConsole.objects.filter(is_active=True)

    if request.method == "POST":
        form = BookingCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                booking = BookingService.create_booking(
                    user=request.user,
                    console_id=cd["game_console"].id,
                    booking_date=cd["booking_date"],
                    start_time=cd["start_time"],
                    duration_hours=cd["duration_hours"],
                    number_of_players=cd["number_of_players"],
                )
                messages.success(request, "Slot available! Proceed to pay the 30% advance.")
                return redirect("payments:payment_page", booking_id=booking.id)
            except ServiceError as e:
                messages.error(request, str(e))
    else:
        form = BookingCreateForm()

    return render(request, "bookings/booking_form.html", {
        "form": form,
        "consoles": consoles,
        "rate_table": {str(k): float(v) for k, v in RATE_PER_PLAYER_HOUR.items()},
        "rate_table_weekend": {str(k): float(v) for k, v in RATE_PER_PLAYER_HOUR_WEEKEND.items()},
        "rate_rows": [
            {
                "players": players,
                "weekday": RATE_PER_PLAYER_HOUR[players],
                "weekend": RATE_PER_PLAYER_HOUR_WEEKEND[players],
            }
            for players in sorted(RATE_PER_PLAYER_HOUR)
        ],
        "form_errors": form.errors if form.is_bound and not form.is_valid() else None,
    })


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
