from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class TournamentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def upcoming(self):
        return self.active().filter(
            status__in=["upcoming", "registrations_open"]
        )


class Tournament(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        REGISTRATIONS_OPEN = "registrations_open", "Registrations Open"
        FULL = "full", "Full"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    game = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    date = models.DateTimeField()
    prize_pool = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    total_slots = models.PositiveIntegerField(default=16)
    registered_slots = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPCOMING,
    )
    image = models.ImageField(
        upload_to="tournaments/",
        blank=True,
        null=True,
        help_text="Upload tournament banner (JPG/PNG, recommended 600x400px)",
    )
    image_url = models.URLField(
        blank=True,
        default="",
        help_text="Fallback: paste an image URL if no file is uploaded above",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TournamentQuerySet.as_manager()

    class Meta:
        ordering = ["date"]
        indexes = [
            models.Index(fields=["status"], name="idx_tourney_status"),
            models.Index(fields=["is_active"], name="idx_tourney_active"),
            models.Index(fields=["date"], name="idx_tourney_date"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.registered_slots > self.total_slots:
            raise ValidationError("Registered slots cannot exceed total slots.")

    @property
    def image_src(self):
        if self.image:
            return self.image.url
        return self.image_url or ""

    @property
    def slots_remaining(self):
        return max(0, self.total_slots - self.registered_slots)

    @property
    def slots_filled_percent(self):
        if self.total_slots == 0:
            return 0
        return int((self.registered_slots / self.total_slots) * 100)

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def status_css_class(self):
        mapping = {
            self.Status.UPCOMING: "tourney-status-upcoming",
            self.Status.REGISTRATIONS_OPEN: "tourney-status-open",
            self.Status.FULL: "tourney-status-upcoming",
            self.Status.IN_PROGRESS: "tourney-status-open",
            self.Status.COMPLETED: "tourney-status-upcoming",
            self.Status.CANCELLED: "tourney-status-upcoming",
        }
        return mapping.get(self.status, "tourney-status-upcoming")

    @property
    def btn_css_class(self):
        if self.status == self.Status.REGISTRATIONS_OPEN:
            return "tourney-btn-primary"
        return "tourney-btn-ghost"

    @property
    def btn_label(self):
        mapping = {
            self.Status.UPCOMING: "Notify Me",
            self.Status.REGISTRATIONS_OPEN: "Register Now",
            self.Status.FULL: "Sold Out",
            self.Status.IN_PROGRESS: "Live Now",
            self.Status.COMPLETED: "Completed",
            self.Status.CANCELLED: "Cancelled",
        }
        return mapping.get(self.status, "Notify Me")
