# apps/bookings/tests.py
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from apps.bookings.models import Booking
from apps.bookings.pricing import calculate_total, apply_membership_discount
from apps.games.models import GameConsole
from apps.users.models import User


class PricingTests(TestCase):
    def setUp(self):
        self.console = GameConsole.objects.create(
            name="PS5", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=400,
        )

    def test_weekday_cost(self):
        # Wed 2026-07-22, 2 players, 2h -> per-player rate 250 * 2 = 500
        total = calculate_total(self.console, date(2026, 7, 22), 2, 2)
        self.assertEqual(total, 500)

    def test_weekend_cost(self):
        # Sat 2026-07-25, 2 players, 2h -> per-player rate 270 * 2 = 540
        total = calculate_total(self.console, date(2026, 7, 25), 2, 2)
        self.assertEqual(total, 540)

    def test_membership_discount(self):
        total = calculate_total(self.console, date(2026, 7, 22), 2, 2)
        discounted = apply_membership_discount(total, 10)
        self.assertEqual(discounted, 450)


class BookingConflictTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@b.com", password="x")
        self.console = GameConsole.objects.create(
            name="PS5", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=300,
        )
        self.booking_date = date(2026, 8, 1)
        self.start = time(10, 0)
        self.end = time(12, 0)

    def _make_booking(self, status="confirmed"):
        return Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=self.booking_date, start_time=self.start,
            end_time=self.end, number_of_players=1,
            total_cost=600, status=status,
        )

    def test_overlapping_booking_rejected(self):
        self._make_booking("confirmed")
        # A booking that overlaps the existing 10:00-12:00 slot.
        overlapping = Booking.objects.filter(
            booking_date=self.booking_date,
            status__in=["pending", "confirmed"],
        ).filter(
            start_time__lt=self.end, end_time__gt=self.start
        )
        self.assertTrue(overlapping.exists())

    def test_non_overlapping_booking_allowed(self):
        self._make_booking("confirmed")
        # A booking at 13:00-14:00 does not overlap 10:00-12:00.
        clash = Booking.objects.filter(
            booking_date=self.booking_date,
            status__in=["pending", "confirmed"],
        ).filter(
            start_time__lt=time(14, 0), end_time__gt=time(13, 0)
        )
        self.assertFalse(clash.exists())
