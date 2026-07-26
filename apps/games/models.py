from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class ConsoleQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def by_type(self, console_type):
        return self.filter(console_type=console_type)

    def available_on_date(self, booking_date):
        """Return consoles not already booked for a given date/time range."""
        return self.active()


class GameConsole(models.Model):
    CONSOLE_TYPES = [
        ("PS5", "PlayStation 5"),
        ("PS4", "PlayStation 4"),
        ("XBOX", "Xbox Series X"),
    ]

    name = models.CharField(max_length=100)
    console_type = models.CharField(max_length=10, choices=CONSOLE_TYPES)
    hourly_rate_weekday = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    hourly_rate_weekend = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to="consoles/", blank=True, null=True)

    objects = ConsoleQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["console_type"], name="idx_console_type"),
            models.Index(fields=["is_active"], name="idx_console_active"),
        ]

    def __str__(self):
        return self.name

    def rate_for_date(self, booking_date):
        if booking_date.weekday() >= 5:
            return self.hourly_rate_weekend
        return self.hourly_rate_weekday


class GameQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def by_category(self, category):
        return self.active().filter(category=category)


class Game(models.Model):
    CATEGORIES = [
        ("action", "Action"),
        ("adventure", "Adventure"),
        ("sports", "Sports"),
        ("racing", "Racing"),
        ("horror", "Horror"),
        ("coop", "Co-op"),
    ]

    BADGE_CHOICES = [
        ("", "None"),
        ("new", "New"),
        ("top_rated", "Top Rated"),
        ("popular", "Popular"),
        ("coop", "Co-op"),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    image = models.ImageField(
        upload_to="games/",
        blank=True,
        null=True,
        help_text="Upload game cover art (JPG/PNG, recommended 400x560px)",
    )
    image_url = models.URLField(
        blank=True,
        default="",
        help_text="Fallback: paste an image URL if no file is uploaded above",
    )
    badge = models.CharField(
        max_length=20,
        choices=BADGE_CHOICES,
        blank=True,
        default="",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("10"))],
        default=Decimal("0"),
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = GameQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["category"], name="idx_game_category"),
            models.Index(fields=["is_active"], name="idx_game_active"),
            models.Index(fields=["sort_order"], name="idx_game_sort"),
        ]

    def __str__(self):
        return self.title

    @property
    def image_src(self):
        if self.image:
            return self.image.url
        return self.image_url or ""

    @property
    def badge_css_class(self):
        mapping = {
            "new": "game-card-badge",
            "top_rated": "game-card-badge-gold",
            "popular": "game-card-badge-red",
            "coop": "game-card-badge-cyan",
        }
        return mapping.get(self.badge, "")

    @property
    def badge_label(self):
        mapping = {
            "new": "New",
            "top_rated": "Top Rated",
            "popular": "Popular",
            "coop": "Co-op",
        }
        return mapping.get(self.badge, "")
