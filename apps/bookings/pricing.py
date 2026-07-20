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

# Player-count multiplier applied to the console's base hourly rate.
# Keyed by number_of_players. 1 player = base rate, more players cost more.
PLAYER_MULTIPLIER = {
    1: Decimal("1.00"),
    2: Decimal("1.60"),
    3: Decimal("2.20"),
    4: Decimal("2.80"),
}

RATE_PER_PLAYER_HOUR = {
    1: Decimal("300"),
    2: Decimal("500"),
    3: Decimal("700"),
    4: Decimal("900"),
}

ADVANCE_PERCENT = Decimal("0.30")


def is_weekend(booking_date: date) -> bool:
    return booking_date.weekday() >= 5


def base_hourly_rate(console, booking_date: date) -> Decimal:
    """Return the console's hourly rate for the given date (weekday/weekend)."""
    if is_weekend(booking_date):
        return console.hourly_rate_weekend
    return console.hourly_rate_weekday


def player_multiplier(number_of_players: int) -> Decimal:
    return PLAYER_MULTIPLIER.get(number_of_players, Decimal("1.00"))


def calculate_total(console, booking_date: date, duration_hours: int,
                    number_of_players: int) -> Decimal:
    """Total cost = base hourly rate (by date) x player multiplier x hours."""
    rate = base_hourly_rate(console, booking_date)
    multiplier = player_multiplier(number_of_players)
    hours = Decimal(str(duration_hours))
    return (rate * multiplier * hours).quantize(Decimal("0.01"))


def apply_membership_discount(total: Decimal, discount_percent: int) -> Decimal:
    """Apply a whole-number membership discount percentage to a total."""
    if not discount_percent:
        return total
    discount = total * (Decimal(str(discount_percent)) / Decimal("100"))
    return (total - discount).quantize(Decimal("0.01"))
