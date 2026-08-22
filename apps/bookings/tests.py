# apps/bookings/tests.py
from datetime import date, time, timedelta

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.pricing import calculate_total, apply_membership_discount
from apps.bookings.services import BookingService
from apps.games.models import GameConsole
from apps.users.models import User
from apps.common.exceptions import (
    BookingConflictError,
    BookingValidationError,
    BookingCannotBeCancelledError,
    BookingInPastError,
    SlotOutsideOperatingHoursError,
    ConsoleNotFoundError,
    BookingNotFoundError,
)


class PricingTests(TestCase):
    def setUp(self):
        self.console = GameConsole.objects.create(
            name="PS5", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=400,
        )

    def test_weekday_cost(self):
        total = calculate_total(self.console, date(2026, 7, 22), 2, 2)
        self.assertEqual(total, 500)

    def test_weekend_cost(self):
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
        overlapping = Booking.objects.filter(
            booking_date=self.booking_date,
            status__in=["pending", "confirmed"],
        ).filter(start_time__lt=self.end, end_time__gt=self.start)
        self.assertTrue(overlapping.exists())

    def test_non_overlapping_booking_allowed(self):
        self._make_booking("confirmed")
        clash = Booking.objects.filter(
            booking_date=self.booking_date,
            status__in=["pending", "confirmed"],
        ).filter(start_time__lt=time(14, 0), end_time__gt=time(13, 0))
        self.assertFalse(clash.exists())


class BookingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="b@test.com", password="x")
        self.console = GameConsole.objects.create(
            name="PS5", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=300,
        )

    @staticmethod
    def _next_weekday(target):
        days_ahead = target - date.today().weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return date.today() + timedelta(days=days_ahead)

    def test_list_for_user(self):
        Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="confirmed",
        )
        qs = BookingService.list_for_user(self.user)
        self.assertEqual(qs.count(), 1)

    def test_list_for_user_with_status_filter(self):
        Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="confirmed",
        )
        Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 2), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="cancelled",
        )
        self.assertEqual(BookingService.list_for_user(self.user, "confirmed").count(), 1)
        self.assertEqual(BookingService.list_for_user(self.user, "cancelled").count(), 1)

    def test_get_for_user_success(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="confirmed",
        )
        result = BookingService.get_for_user(self.user, booking.id)
        self.assertEqual(result.id, booking.id)

    def test_get_for_user_not_found(self):
        with self.assertRaises(BookingNotFoundError):
            BookingService.get_for_user(self.user, 9999)

    def test_get_for_user_wrong_user(self):
        other_user = User.objects.create_user(email="other@b.com", password="x")
        booking = Booking.objects.create(
            user=other_user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="confirmed",
        )
        with self.assertRaises(BookingNotFoundError):
            BookingService.get_for_user(self.user, booking.id)

    def test_cancel_booking_success(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="pending",
        )
        result = BookingService.cancel_booking(self.user, booking.id)
        result.refresh_from_db()
        self.assertEqual(result.status, "cancelled")

    def test_cancel_booking_cannot_cancel_completed(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="completed",
        )
        with self.assertRaises(BookingCannotBeCancelledError):
            BookingService.cancel_booking(self.user, booking.id)

    def test_invalid_player_count(self):
        future_date = date.today() + timedelta(days=30)
        with self.assertRaises(BookingValidationError):
            BookingService.create_booking(
                self.user, self.console.id, future_date,
                time(10, 0), 2, 5,  # 5 is invalid
            )

    def test_console_not_found(self):
        future_date = date.today() + timedelta(days=30)
        with self.assertRaises(ConsoleNotFoundError):
            BookingService.create_booking(
                self.user, 9999, future_date,
                time(10, 0), 2, 2,
            )

    def test_booking_in_past(self):
        past_date = date.today() - timedelta(days=1)
        with self.assertRaises(BookingInPastError):
            BookingService.create_booking(
                self.user, self.console.id, past_date,
                time(10, 0), 2, 2,
            )

    def test_slot_outside_operating_hours_weekday(self):
        future_date = self._next_weekday(0)  # next Monday
        with self.assertRaises(SlotOutsideOperatingHoursError):
            BookingService.create_booking(
                self.user, self.console.id, future_date,
                time(8, 0), 2, 2,  # Before 10 AM
            )

    def test_slot_conflict_detection(self):
        future_date = self._next_weekday(0)  # next Monday
        Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=future_date, start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="confirmed",
        )
        with self.assertRaises(BookingConflictError):
            BookingService.create_booking(
                self.user, self.console.id, future_date,
                time(10, 0), 2, 1,  # Overlaps with existing
            )


class BookingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="model@b.com", password="x")
        self.console = GameConsole.objects.create(
            name="PS5", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=300,
        )

    def test_booking_str(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=2,
            total_cost=500, status="pending",
        )
        self.assertIn("Booking #", str(booking))
        self.assertIn("model@b.com", str(booking))

    def test_duration_hours(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 30), number_of_players=2,
            total_cost=500, status="pending",
        )
        self.assertEqual(booking.duration_hours, 2.5)

    def test_duration_hours_midnight_crossing(self):
        booking = Booking(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(23, 0),
            end_time=time(1, 0), number_of_players=2, total_cost=500,
        )
        self.assertEqual(booking.duration_hours, 2.0)

    def test_duration_hours_ends_at_midnight(self):
        booking = Booking(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(23, 0),
            end_time=time(0, 0), number_of_players=2, total_cost=500,
        )
        self.assertEqual(booking.duration_hours, 1.0)

    def test_duration_hours_same_day_one_hour(self):
        booking = Booking(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(22, 0),
            end_time=time(23, 0), number_of_players=2, total_cost=500,
        )
        self.assertEqual(booking.duration_hours, 1.0)

    def test_duration_hours_morning_slot(self):
        booking = Booking(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(9, 0),
            end_time=time(10, 0), number_of_players=2, total_cost=500,
        )
        self.assertEqual(booking.duration_hours, 1.0)

    def test_duration_hours_half_hour_boundaries(self):
        booking = Booking(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(12, 30),
            end_time=time(14, 30), number_of_players=2, total_cost=500,
        )
        self.assertEqual(booking.duration_hours, 2.0)

    def test_advance_amount(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=2,
            total_cost=500, status="pending",
        )
        self.assertEqual(booking.advance_amount, 150.00)

    def test_balance_amount(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=2,
            total_cost=500, status="pending",
        )
        self.assertEqual(booking.balance_amount, 350.00)

    def test_queryset_active(self):
        Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="pending",
        )
        Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 2), start_time=time(10, 0),
            end_time=time(12, 0), number_of_players=1,
            total_cost=600, status="cancelled",
        )
        self.assertEqual(Booking.objects.active().count(), 1)
