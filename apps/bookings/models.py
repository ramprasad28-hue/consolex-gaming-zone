from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class BookingQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user).select_related("game_console", "payment")

    def active(self):
        return self.filter(status__in=["pending", "confirmed"])

    def confirmed(self):
        return self.filter(status="confirmed")

    def completed(self):
        return self.filter(status="completed")

    def cancelled(self):
        return self.filter(status="cancelled")

    def upcoming_for_user(self, user):
        return self.for_user(user).filter(
            status__in=["pending", "confirmed"]
        ).order_by("booking_date", "start_time")

    def live(self):
        """Bookings currently checked in (live sessions in progress)."""
        return self.filter(
            checked_in_at__isnull=False,
            status__in=["confirmed", "checked_in"],
        )


class Booking(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("checked_in", "Checked In"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    game_console = models.ForeignKey(
        "games.GameConsole",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bookings",
    )
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    number_of_players = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ["-booking_date", "-start_time"]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_booking_user_status"),
            models.Index(fields=["booking_date", "start_time"], name="idx_booking_date_time"),
            models.Index(fields=["game_console", "booking_date"], name="idx_booking_console_date"),
            models.Index(fields=["status"], name="idx_booking_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(number_of_players__gte=1) & models.Q(number_of_players__lte=4),
                name="chk_booking_players_range",
            ),
        ]

    def __str__(self):
        return (
            f"Booking #{self.id} — {self.user.email} — "
            f"{self.booking_date} {self.start_time}"
        )

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")

    @property
    def duration_hours(self):
        from datetime import datetime, date
        start = datetime.combine(date.today(), self.start_time)
        end = datetime.combine(date.today(), self.end_time)
        diff = (end - start).seconds / 3600
        return round(diff, 2)

    @property
    def advance_amount(self):
        return (self.total_cost * Decimal("0.30")).quantize(Decimal("0.01"))

    @property
    def balance_amount(self):
        return self.total_cost - self.advance_amount

    @property
    def is_paid(self):
        return (
            hasattr(self, "payment")
            and self.payment.status == "captured"
        )

    @property
    def is_checked_in(self):
        return self.checked_in_at is not None

    @property
    def session_remaining_minutes(self):
        """Minutes left in the session window (0 if ended)."""
        if not self.is_checked_in:
            return 0
        from datetime import datetime, date as date_type, timedelta
        base = date_type.today()
        start = datetime.combine(base, self.start_time)
        end = datetime.combine(base, self.end_time)
        if end <= start:
            end += timedelta(days=1)
        now_dt = datetime.combine(base, timezone.now().time())
        remaining = (end - now_dt).total_seconds() / 60
        return max(0, round(remaining))
