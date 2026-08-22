# apps/bookings/tests.py
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

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

    def test_duration_hours_late_night_three_hours(self):
        booking = Booking(
            user=self.user, game_console=self.console,
            booking_date=date(2026, 9, 1), start_time=time(23, 30),
            end_time=time(2, 30), number_of_players=2, total_cost=500,
        )
        self.assertEqual(booking.duration_hours, 3.0)

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


class SlotAvailabilityServiceTests(TestCase):
    """BookingService.get_day_availability — real slot availability."""

    def setUp(self):
        self.user = User.objects.create_user(email="avail@test.com", password="x")
        self.console_a = GameConsole.objects.create(
            name="PS5 A", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=300,
        )
        self.console_b = GameConsole.objects.create(
            name="PS5 B", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=300,
        )
        # Fixed future dates relative to test run (2026+)
        self.wednesday = timezone.localdate() + timedelta(days=(2 - timezone.localdate().weekday()) % 7 or 7)
        self.saturday = self.wednesday + timedelta(days=3)

    def _make_booking(self, start, end, console=None, booking_date=None,
                      status="confirmed", with_payment=False):
        b = Booking.objects.create(
            user=self.user,
            game_console=console or self.console_a,
            booking_date=booking_date or self.wednesday,
            start_time=start, end_time=end,
            number_of_players=1, total_cost=600, status=status,
        )
        if with_payment:
            from apps.payments.models import Payment
            Payment.objects.create(booking=b, user=self.user, amount=18000)
        return b

    def _starts(self, result):
        return [s["start"] for s in result["slots"]]

    def _by_start(self, result):
        return {s["start"]: s for s in result["slots"]}

    # ── Grid shape ────────────────────────────────────────

    def test_free_weekday_grid_30min_intervals(self):
        r = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        starts = self._starts(r)
        self.assertEqual(len(starts), 25)          # 10:00..22:00 every :30
        self.assertEqual(starts[0], "10:00")
        self.assertEqual(starts[-1], "22:00")
        self.assertTrue(all(s["available"] for s in r["slots"]))
        self.assertEqual(r["interval_minutes"], 30)

    def test_free_weekend_grid_ends_midnight(self):
        r = BookingService.get_day_availability(self.console_a.id, self.saturday, 1)
        starts = self._starts(r)
        self.assertEqual(starts[0], "09:00")
        self.assertEqual(starts[-1], "23:00")      # ends exactly at midnight
        last = self._by_start(r)["23:00"]
        self.assertEqual(last["end"], "00:00")

    def test_weekday_no_slot_ends_after_close(self):
        for duration in (1, 2, 4):
            r = BookingService.get_day_availability(self.console_a.id, self.wednesday, duration)
            # last slot must end by 23:00
            last = r["slots"][-1]
            h, m = last["end"].split(":")
            self.assertLessEqual(int(h), 23)

    # ── Overlap semantics (approval examples) ─────────────

    def test_existing_noon_to_1pm_blocks_overlaps_only(self):
        """Existing 12:00–13:00: 12:00 & 12:30 unavailable; 11:00 & 13:00 available."""
        self._make_booking(time(12, 0), time(13, 0))
        r = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        slots = self._by_start(r)
        self.assertFalse(slots["12:00"]["available"])
        self.assertFalse(slots["12:30"]["available"])
        self.assertTrue(slots["11:00"]["available"])   # touching start boundary
        self.assertTrue(slots["13:00"]["available"])   # touching end boundary

    def test_requested_1130_blocked_by_noon_booking(self):
        """Existing 12:00–13:00 vs requested 11:30–12:30 → overlap → unavailable."""
        self._make_booking(time(12, 0), time(13, 0))
        r = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        self.assertFalse(self._by_start(r)["11:30"]["available"])

    # ── Blocking statuses ─────────────────────────────────

    def test_unpaid_pending_does_not_block(self):
        self._make_booking(time(12, 0), time(13, 0), status="pending")
        r = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        self.assertTrue(all(s["available"] for s in r["slots"]))

    def test_paid_pending_blocks(self):
        self._make_booking(time(12, 0), time(13, 0), status="pending", with_payment=True)
        r = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        slots = self._by_start(r)
        self.assertFalse(slots["12:00"]["available"])
        self.assertFalse(slots["12:30"]["available"])
        self.assertTrue(slots["13:00"]["available"])

    def test_cancelled_does_not_block(self):
        self._make_booking(time(12, 0), time(13, 0), status="cancelled", with_payment=True)
        r = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        self.assertTrue(all(s["available"] for s in r["slots"]))

    # ── Independence ──────────────────────────────────────

    def test_other_console_independent(self):
        self._make_booking(time(12, 0), time(13, 0))
        r_b = BookingService.get_day_availability(self.console_b.id, self.wednesday, 1)
        self.assertTrue(all(s["available"] for s in r_b["slots"]))
        r_a = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        self.assertFalse(self._by_start(r_a)["12:00"]["available"])

    def test_other_date_independent(self):
        self._make_booking(time(12, 0), time(13, 0))
        other_day = self.wednesday + timedelta(days=7)
        r = BookingService.get_day_availability(self.console_a.id, other_day, 1)
        self.assertTrue(all(s["available"] for s in r["slots"]))

    # ── Duration effect ───────────────────────────────────

    def test_duration_extends_blocked_range(self):
        """Existing 12:00–13:00, duration 2h: starts 10:30/11:00/11:30 blocked."""
        self._make_booking(time(12, 0), time(13, 0))
        r = BookingService.get_day_availability(self.console_a.id, self.wednesday, 2)
        slots = self._by_start(r)
        self.assertFalse(slots["10:30"]["available"])  # 10:30–12:30 overlaps
        self.assertFalse(slots["11:00"]["available"])  # 11:00–13:00 overlaps
        self.assertFalse(slots["11:30"]["available"])  # 11:30–13:30 overlaps
        self.assertTrue(slots["13:00"]["available"])   # 13:00–15:00 free
        self.assertTrue(slots["10:00"]["available"])   # 10:00–12:00 touches boundary

    def test_duration_shrinks_grid_at_close(self):
        r1 = BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)
        r4 = BookingService.get_day_availability(self.console_a.id, self.wednesday, 4)
        self.assertGreater(len(r1["slots"]), len(r4["slots"]))
        self.assertEqual(self._starts(r4)[-1], "19:00")  # 19:00–23:00 last

    # ── Past-slot rule ────────────────────────────────────

    def test_past_date_all_unavailable(self):
        past = timezone.localdate() - timedelta(days=3)
        r = BookingService.get_day_availability(self.console_a.id, past, 1)
        self.assertTrue(r["slots"])
        self.assertTrue(all(not s["available"] for s in r["slots"]))
        self.assertEqual(r["slots"][0]["reason"], "past")

    def test_today_past_starts_unavailable_future_available(self):
        # Same clock source as _is_past_slot (local wall clock)
        now = timezone.localtime()
        today = now.date()
        r = BookingService.get_day_availability(self.console_a.id, today, 1)
        for s in r["slots"]:
            slot_now = time(*map(int, s["start"].split(":")))
            if slot_now <= now.time():
                self.assertFalse(s["available"], s["start"])
            else:
                self.assertTrue(s["available"], s["start"])

    # ── Validation ────────────────────────────────────────

    def test_invalid_console_raises(self):
        with self.assertRaises(ConsoleNotFoundError):
            BookingService.get_day_availability(99999, self.wednesday, 1)

    def test_inactive_console_raises(self):
        self.console_a.is_active = False
        self.console_a.save()
        with self.assertRaises(ConsoleNotFoundError):
            BookingService.get_day_availability(self.console_a.id, self.wednesday, 1)

    def test_invalid_durations_raise(self):
        for bad in (0, 11, "abc", None):
            with self.assertRaises(BookingValidationError):
                BookingService.get_day_availability(self.console_a.id, self.wednesday, bad)


class AvailabilityApiTests(TestCase):
    """GET /api/v1/bookings/availability/ — auth, shape, errors."""

    def setUp(self):
        self.user = User.objects.create_user(email="api@x.com", password="testpass123")
        self.console = GameConsole.objects.create(
            name="PS5 API", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=300,
        )
        self.url = "/api/v1/bookings/availability/"
        self.future_wed = timezone.localdate() + timedelta(days=(2 - timezone.localdate().weekday()) % 7 or 7)

    def test_requires_authentication(self):
        # DRF SessionAuthentication returns 403 (no challenge) for anonymous
        resp = self.client.get(self.url, {"console": self.console.id, "date": str(self.future_wed)})
        self.assertEqual(resp.status_code, 403)

    def test_returns_slot_shape_for_authenticated_user(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url, {
            "console": self.console.id, "date": str(self.future_wed), "duration": "1",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["console_id"], self.console.id)
        self.assertEqual(data["duration_hours"], 1)
        self.assertEqual(data["interval_minutes"], 30)
        self.assertTrue(data["slots"])
        first = data["slots"][0]
        self.assertIn("start", first)
        self.assertIn("end", first)
        self.assertIn("available", first)

    def test_missing_params_400(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 400)

    def test_bad_date_400(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url, {"console": self.console.id, "date": "not-a-date"})
        self.assertEqual(resp.status_code, 400)

    def test_unknown_console_404(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url, {"console": 99999, "date": str(self.future_wed)})
        self.assertEqual(resp.status_code, 404)


class FinalSubmissionConflictTests(TestCase):
    """Race protection: availability is advisory; create_booking stays authoritative."""

    def setUp(self):
        self.user = User.objects.create_user(email="race@x.com", password="x")
        self.other = User.objects.create_user(email="other@x.com", password="x")
        self.console = GameConsole.objects.create(
            name="PS5 Race", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=300,
        )
        self.wednesday = timezone.localdate() + timedelta(days=(2 - timezone.localdate().weekday()) % 7 or 7)

    def test_conflict_rejected_even_if_availability_was_stale(self):
        """Slot looked free during availability check, booked before submit."""
        # Simulate Customer B winning the race:
        winner = Booking.objects.create(
            user=self.other, game_console=self.console,
            booking_date=self.wednesday, start_time=time(12, 0),
            end_time=time(13, 0), number_of_players=1,
            total_cost=600, status="confirmed",
        )
        # Availability would now show 12:30 unavailable...
        r = BookingService.get_day_availability(self.console.id, self.wednesday, 1)
        by_start = {s["start"]: s for s in r["slots"]}
        self.assertFalse(by_start["12:30"]["available"])
        # ...and create_booking rejects Customer A regardless.
        with self.assertRaises(BookingConflictError):
            BookingService.create_booking(
                user=self.user, console_id=self.console.id,
                booking_date=self.wednesday, start_time=time(12, 30),
                duration_hours=1, number_of_players=2,
            )

    def test_touching_boundary_still_allowed_on_submit(self):
        BookingService.create_booking(
            user=self.user, console_id=self.console.id,
            booking_date=self.wednesday, start_time=time(12, 0),
            duration_hours=1, number_of_players=1,
        )
        b2 = BookingService.create_booking(
            user=self.user, console_id=self.console.id,
            booking_date=self.wednesday, start_time=time(13, 0),
            duration_hours=1, number_of_players=1,
        )
        self.assertEqual(b2.start_time, time(13, 0))


class PastSlotRuleTests(TestCase):
    """
    _is_past_slot must compare against the LOCAL (IST) wall clock.

    Regression guard: timezone.now() returns UTC under USE_TZ, so the old
    `now.time()` comparison lagged IST by 5h30m and accepted slots up to
    5h30m in the past. Each test injects an aware "now" so behavior is
    deterministic regardless of when the suite runs.
    """

    IST = ZoneInfo("Asia/Kolkata")

    @staticmethod
    def _ist_now(*args):
        return datetime(*args, tzinfo=PastSlotRuleTests.IST)

    def test_slot_30min_in_past_is_rejected(self):
        # 3:30 PM IST: a 3:00 PM slot today is past (old code accepted it)
        now = self._ist_now(2026, 8, 19, 15, 30)
        self.assertTrue(BookingService._is_past_slot(date(2026, 8, 19), time(15, 0), now=now))

    def test_slot_starting_exactly_now_is_rejected(self):
        now = self._ist_now(2026, 8, 19, 15, 30)
        self.assertTrue(BookingService._is_past_slot(date(2026, 8, 19), time(15, 30), now=now))

    def test_future_slot_today_is_accepted(self):
        now = self._ist_now(2026, 8, 19, 15, 30)
        self.assertFalse(BookingService._is_past_slot(date(2026, 8, 19), time(16, 0), now=now))

    def test_tomorrow_morning_is_accepted(self):
        now = self._ist_now(2026, 8, 19, 15, 30)
        self.assertFalse(BookingService._is_past_slot(date(2026, 8, 20), time(9, 0), now=now))

    def test_utc_vs_local_divergence_pinned(self):
        # The actual bug scenario expressed on the UTC clock:
        # now == 10:00 UTC == 3:30 PM IST. A 3:00 PM IST slot is past,
        # even though 15:00 > 10:00 numerically.
        utc_now = datetime(2026, 8, 19, 10, 0, tzinfo=dt_timezone.utc)
        self.assertTrue(BookingService._is_past_slot(date(2026, 8, 19), time(15, 0), now=utc_now))

    def test_weekend_late_evening_past_slot_rejected(self):
        # Sat 11:59 PM IST: a 7:30 PM slot is ~4.5h past (worst-case window)
        now = self._ist_now(2026, 8, 22, 23, 59)  # Saturday
        self.assertTrue(BookingService._is_past_slot(date(2026, 8, 22), time(19, 30), now=now))
