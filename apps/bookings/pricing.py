# apps/bookings/pricing.py
"""
Single source of truth for booking price calculation.

Pricing model
-------------
A booking's hourly rate is the selected console's base hourly rate
(weekday vs weekend, chosen from the booking date) multiplied by a
player-count multiplier. Player multipliers live here so they can be
tuned without a code deploy-unfriendly hardcoded dict scattered around.

Weekend = Saturday (5) and Sunday (6) per Python's datetime weekday().
"""
from datetime import date
from decimal import Decimal

# Standard pay-per-hour rates (CONSOLEX business model) when NOT using a
# membership. Absolute per-player hourly rates, split by weekday/weekend.
# Prices are taken directly from the CONSOLEX rate card.
RATE_PER_PLAYER_HOUR = {
    1: Decimal("130"),
    2: Decimal("250"),
    3: Decimal("330"),
    4: Decimal("420"),
}

RATE_PER_PLAYER_HOUR_WEEKEND = {
    1: Decimal("150"),
    2: Decimal("270"),
    3: Decimal("400"),
    4: Decimal("520"),
}

ADVANCE_PERCENT = Decimal("0.30")


def is_weekend(booking_date: date) -> bool:
    return booking_date.weekday() >= 5


def base_hourly_rate(console, booking_date: date) -> Decimal:
    """Return the console's hourly rate for the given date (weekday/weekend)."""
    if is_weekend(booking_date):
        return console.hourly_rate_weekend
    return console.hourly_rate_weekday


def player_hourly_rate(number_of_players: int, booking_date: date) -> Decimal:
    """Absolute per-player hourly rate for the given date (weekday/weekend)."""
    table = (
        RATE_PER_PLAYER_HOUR_WEEKEND
        if is_weekend(booking_date)
        else RATE_PER_PLAYER_HOUR
    )
    return table.get(number_of_players, Decimal("0"))


def calculate_total(console, booking_date: date, duration_hours: int,
                    number_of_players: int) -> Decimal:
    """Total cost = per-player hourly rate (by date) x hours."""
    rate = player_hourly_rate(number_of_players, booking_date)
    hours = Decimal(str(duration_hours))
    return (rate * hours).quantize(Decimal("0.01"))


def apply_membership_discount(total: Decimal, discount_percent: int) -> Decimal:
    """Apply a whole-number membership discount percentage to a total."""
    if not discount_percent:
        return total
    discount = total * (Decimal(str(discount_percent)) / Decimal("100"))
    return (total - discount).quantize(Decimal("0.01"))
