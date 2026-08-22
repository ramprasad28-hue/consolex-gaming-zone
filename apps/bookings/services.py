"""
Business logic for bookings: creation, conflict detection, cancellation.

Views and API endpoints delegate here instead of inlining logic.
"""
import logging
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.pricing import (
    calculate_total,
    apply_membership_discount,
    RATE_PER_PLAYER_HOUR,
)
from apps.games.models import GameConsole
from apps.memberships.models import MembershipSubscription
from apps.common.exceptions import (
    BookingConflictError,
    BookingValidationError,
    BookingNotFoundError,
    BookingCannotBeCancelledError,
    BookingInPastError,
    SlotOutsideOperatingHoursError,
    ConsoleNotFoundError,
)

logger = logging.getLogger("apps.bookings")


class BookingService:
    """Stateless service — every method is a self-contained operation."""

    # Start-time grid granularity for availability (business rule: 30 min).
    SLOT_INTERVAL_MINUTES = 30

    # ── Queries ────────────────────────────────────────────

    @staticmethod
    def list_for_user(user, status_filter=None):
        qs = Booking.objects.filter(user=user).select_related("game_console", "payment")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("-booking_date", "-start_time")

    @staticmethod
    def get_for_user(user, booking_id):
        try:
            return Booking.objects.select_related("game_console", "payment").get(
                pk=booking_id, user=user
            )
        except Booking.DoesNotExist:
            raise BookingNotFoundError(f"Booking #{booking_id} not found.")

    # ── Booking creation ───────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_booking(user, console_id, booking_date, start_time, duration_hours, number_of_players):
        """
        Create a booking with full validation, conflict detection, and pricing.

        Returns the created Booking instance.
        Raises BookingValidationError / BookingConflictError on failure.
        """
        # Validate player count
        if number_of_players not in RATE_PER_PLAYER_HOUR:
            raise BookingValidationError("Invalid number of players selected.")

        # Resolve console
        try:
            console = GameConsole.objects.get(pk=console_id, is_active=True)
        except (GameConsole.DoesNotExist, ValueError):
            raise ConsoleNotFoundError("Console not found.")

        # Compute end time
        start_dt = datetime.combine(booking_date, start_time)
        end_dt = start_dt + timedelta(hours=duration_hours)
        end_time = end_dt.time()

        # Reject past slots (local wall clock — session times are local times)
        if BookingService._is_past_slot(booking_date, start_time):
            raise BookingInPastError("Please choose a future date and time.")

        # Operating hours check
        BookingService._validate_operating_hours(booking_date, start_time, end_dt)

        # Auto-cancel stale unpaid pending bookings (>30 min old)
        BookingService._cleanup_stale_pending(user)

        # Conflict detection (serialized with row-level lock)
        BookingService._check_slot_conflict(console, booking_date, start_time, end_time)

        # Pricing
        total_cost = BookingService._calculate_cost(user, console, booking_date, duration_hours, number_of_players)

        booking = Booking.objects.create(
            user=user,
            game_console=console,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            number_of_players=number_of_players,
            total_cost=total_cost,
            status="pending",
        )

        logger.info(
            "Booking #%s created for %s on %s %s-%s (%s players, ₹%s)",
            booking.id, user.email, booking_date, start_time, end_time,
            number_of_players, total_cost,
        )
        return booking

    # ── Cancellation ───────────────────────────────────────

    @staticmethod
    def cancel_booking(user, booking_id):
        booking = BookingService.get_for_user(user, booking_id)

        if booking.status not in ("pending", "confirmed"):
            raise BookingCannotBeCancelledError(
                "This booking cannot be cancelled."
            )

        booking.status = "cancelled"
        booking.save(update_fields=["status", "updated_at"])

        logger.info("Booking #%s cancelled by %s", booking.id, user.email)
        return booking

    # ── Check-in / check-out (staff) ──────────────────────

    @staticmethod
    def get(booking_id):
        """Fetch a booking by id with related objects for staff operations."""
        try:
            return Booking.objects.select_related("user", "game_console", "payment").get(
                pk=booking_id
            )
        except Booking.DoesNotExist:
            raise BookingNotFoundError(f"Booking #{booking_id} not found.")

    @staticmethod
    def check_in(booking_id, staff):
        """
        Mark a confirmed booking as checked in (session started).

        Raises BookingValidationError if the booking can't be checked in.
        """
        booking = BookingService.get(booking_id)

        if booking.checked_in_at is not None:
            raise BookingValidationError("This booking is already checked in.")

        if booking.status != "confirmed":
            raise BookingValidationError(
                "Only confirmed bookings can be checked in."
            )

        booking.checked_in_at = timezone.now()
        booking.status = "checked_in"
        booking.save(update_fields=["checked_in_at", "status", "updated_at"])

        logger.info(
            "Booking #%s checked in by %s at %s",
            booking.id, staff.email, booking.checked_in_at,
        )
        return booking

    @staticmethod
    def check_out(booking_id, staff):
        """
        Complete a live session and mark the booking completed.
        """
        booking = BookingService.get(booking_id)

        if booking.checked_in_at is None:
            raise BookingValidationError("This booking is not checked in.")

        booking.checked_in_at = None
        booking.status = "completed"
        booking.save(update_fields=["checked_in_at", "status", "updated_at"])

        logger.info(
            "Booking #%s checked out by %s",
            booking.id, staff.email,
        )
        return booking

    # ── Availability ───────────────────────────────────────

    @staticmethod
    def _operating_hours(booking_date):
        """
        Single source of truth for daily operating hours.

        Returns (open_hour, close_hour) in 24h terms:
          weekday 10:00–23:00, weekend 09:00–24:00.
        """
        is_weekend = booking_date.weekday() >= 5
        return (9 if is_weekend else 10), (24 if is_weekend else 23)

    @staticmethod
    def get_day_availability(console_id, booking_date, duration_hours):
        """
        Real slot availability for one console/day, computed with the SAME
        business rules as create_booking:

          - operating hours via the shared _operating_hours helper
          - past-slot rejection (same comparison)
          - strict-overlap conflict predicate against blocking bookings
            (confirmed + paid pending), matching _check_slot_conflict

        Start times are generated every SLOT_INTERVAL_MINUTES. The result is
        advisory only — create_booking remains the final authority at
        submission time (row-locked conflict check).
        """
        try:
            console = GameConsole.objects.get(pk=console_id, is_active=True)
        except (GameConsole.DoesNotExist, ValueError):
            raise ConsoleNotFoundError("Console not found.")

        try:
            duration = int(duration_hours)
        except (TypeError, ValueError):
            raise BookingValidationError("Invalid duration selected.")
        if duration < 1 or duration > 10:
            raise BookingValidationError("Invalid duration selected.")

        is_weekend = booking_date.weekday() >= 5
        open_hour, close_hour = BookingService._operating_hours(booking_date)

        now_local = timezone.localtime()

        # Blocking bookings for this console/day — same statuses the
        # submission-time conflict check treats as conflicts.
        blocking = list(
            Booking.objects.filter(
                game_console=console,
                booking_date=booking_date,
            ).filter(
                Q(status="confirmed") | Q(status="pending", payment__isnull=False)
            ).values_list("start_time", "end_time")
        )

        # Latest allowed session end per business hours:
        #   weekday: same-day close_hour; weekend: midnight next day.
        if is_weekend:
            max_end = datetime.combine(booking_date + timedelta(days=1), time(0, 0))
        else:
            max_end = datetime.combine(booking_date, time(close_hour))

        interval = timedelta(minutes=BookingService.SLOT_INTERVAL_MINUTES)
        start_dt = datetime.combine(booking_date, time(open_hour))

        slots = []
        while True:
            end_dt = start_dt + timedelta(hours=duration)
            if end_dt > max_end:
                break

            if BookingService._is_past_slot(booking_date, start_dt.time(), now=now_local):
                available, reason = False, "past"
            else:
                s_t, e_t = start_dt.time(), end_dt.time()
                overlaps = any(
                    s_t < b_end and e_t > b_start for b_start, b_end in blocking
                )
                available, reason = (not overlaps), (None if not overlaps else "booked")

            slot = {
                "start": start_dt.strftime("%H:%M"),
                "end": end_dt.strftime("%H:%M"),
                "available": available,
            }
            if reason:
                slot["reason"] = reason
            slots.append(slot)
            start_dt += interval

        return {
            "console_id": console.id,
            "date": booking_date.isoformat(),
            "duration_hours": duration,
            "interval_minutes": BookingService.SLOT_INTERVAL_MINUTES,
            "slots": slots,
        }

    # ── Internal helpers ───────────────────────────────────

    @staticmethod
    def _is_past_slot(booking_date, start_time, now=None):
        """
        True if the slot starts at or before "now" on the local wall clock.

        Booking date/times are naive local session times (IST), so the
        reference clock must be timezone.localtime(), not timezone.now()
        (which is UTC under USE_TZ). An aware `now` is converted to local
        time first; `now` may also be injected naive-local for tests.
        """
        if now is None:
            now = timezone.localtime()
        elif timezone.is_aware(now):
            now = timezone.localtime(now)
        return booking_date < now.date() or (
            booking_date == now.date() and start_time <= now.time()
        )

    @staticmethod
    def _validate_operating_hours(booking_date, start_time, end_dt):
        """Raise if outside operating hours (weekdays 10–23, weekends 9–24)."""
        open_hour, close_hour = BookingService._operating_hours(booking_date)
        is_weekend = booking_date.weekday() >= 5

        if start_time.hour < open_hour:
            label = "9 AM on weekends" if is_weekend else "10 AM on weekdays"
            raise SlotOutsideOperatingHoursError(f"We open at {label}.")

        end_hour = end_dt.hour if end_dt.hour != 0 else (24 if is_weekend else 0)
        if end_hour > close_hour:
            label = "midnight on weekends" if is_weekend else "11 PM on weekdays"
            raise SlotOutsideOperatingHoursError(
                f"We close at {label}. Choose an earlier time or shorter duration."
            )

    @staticmethod
    def _cleanup_stale_pending(user):
        """Auto-cancel pending bookings older than 30 minutes with no payment."""
        cutoff = timezone.now() - timedelta(minutes=30)
        stale = Booking.objects.filter(
            user=user,
            status="pending",
            created_at__lt=cutoff,
            payment__isnull=True,
        )
        if stale.exists():
            count = stale.count()
            stale.update(status="cancelled")
            logger.info("Auto-cancelled %d stale pending bookings for user %d", count, user.pk)

    @staticmethod
    def _check_slot_conflict(console, booking_date, start_time, end_time):
        """
        Serialized conflict detection using select_for_update.

        Blocks on:
          - confirmed bookings (always)
          - pending bookings that have an associated payment (partially paid)
        Ignores unpaid pending bookings (stale abandoned sessions).
        """
        GameConsole.objects.select_for_update().get(pk=console.pk)

        conflict_filter = (
            Q(booking_date=booking_date)
            & Q(start_time__lt=end_time)
            & Q(end_time__gt=start_time)
            & Q(game_console=console)
            & (
                Q(status="confirmed")
                | (Q(status="pending") & Q(payment__isnull=False))
            )
        )
        if Booking.objects.filter(conflict_filter).exists():
            raise BookingConflictError("This time slot is already booked.")

    @staticmethod
    def _calculate_cost(user, console, booking_date, duration_hours, number_of_players):
        """Calculate total cost, applying membership discounts and free hours."""
        total_cost = calculate_total(console, booking_date, duration_hours, number_of_players)

        # Apply legacy membership discount
        if getattr(user, "membership", None):
            total_cost = apply_membership_discount(
                total_cost, user.membership.discount_percent
            )

        # Check active subscription for free hours
        active_sub = MembershipSubscription.objects.filter(
            user=user,
            status=MembershipSubscription.STATUS_ACTIVE,
            expires_at__gt=timezone.now(),
        ).select_related("plan").first()

        if active_sub:
            total_hours = (
                active_sub.plan.included_hours
                + active_sub.plan.weekend_hours
                + active_sub.plan.bonus_hours
            )
            if total_hours > 0:
                total_cost = Decimal("0")

        return total_cost
