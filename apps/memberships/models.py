from django.conf import settings
from django.db import models
from django.utils import timezone


class Membership(models.Model):
    """
    Master catalog of purchasable membership plans (e.g. Free, Silver,
    Gold, Platinum). This model represents *what can be bought* — it does
    not track who owns it or for how long. See MembershipSubscription for
    that.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(
        help_text="Membership validity in days"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate to retire a plan without deleting its history.",
    )

    discount_percent = models.PositiveIntegerField(
        default=0,
        help_text="Booking discount this plan grants, as a whole percentage "
        "(0-100).",
    )
    priority_booking = models.BooleanField(
        default=False,
        help_text="Whether members on this plan get priority booking access.",
    )
    free_hours_per_month = models.PositiveIntegerField(
        default=0,
        help_text="Complimentary gaming hours included per month on this plan.",
    )

    # ── Real CONSOLEX plan fields (additive) ──
    included_hours = models.PositiveIntegerField(
        default=0,
        help_text="Weekday gaming hours included in the plan.",
    )
    weekend_hours = models.PositiveIntegerField(
        default=0,
        help_text="Additional weekend gaming hours included in the plan.",
    )
    bonus_hours = models.PositiveIntegerField(
        default=0,
        help_text="Bonus hours (e.g. rollover/extra) included in the plan.",
    )
    badge_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Hex color (e.g. #00D9FF) used to render this tier's badge "
        "consistently across the site.",
    )
    tier_level = models.PositiveIntegerField(
        default=0,
        help_text="Numeric rank used to compare plans (e.g. Free=0, Silver=1, "
        "Gold=2, Platinum=3).",
    )
    is_popular = models.BooleanField(
        default=False,
        help_text="Highlights this plan as the recommended/most popular choice "
        "on the pricing page.",
    )

    class Meta:
        ordering = ["tier_level", "price"]

    def __str__(self):
        return self.name


class MembershipSubscription(models.Model):
    """A user's membership: which plan, when it started/expires, status."""

    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_PENDING = "pending"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_PENDING, "Pending"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The member this subscription belongs to.",
    )
    plan = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        help_text="Which plan this subscription is for.",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Current lifecycle state of this subscription.",
    )
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this subscription began.",
    )
    expires_at = models.DateTimeField(
        help_text="When this subscription expires."
    )
    auto_renew = models.BooleanField(
        default=False,
        help_text="Whether this subscription should automatically renew.",
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of cancellation/upgrade/downgrade.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="unique_active_subscription_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.plan.name} ({self.status})"

    @property
    def is_active_valid(self):
        return self.status == self.STATUS_ACTIVE and self.expires_at > timezone.now()

    @property
    def days_remaining(self):
        remaining = (self.expires_at - timezone.now()).days
        return max(remaining, 0)


class LoyaltyProfile(models.Model):
    """A lightweight, always-one-row-per-user rollup of a member's activity."""

    LEVEL_BRONZE = "bronze"
    LEVEL_SILVER = "silver"
    LEVEL_GOLD = "gold"
    LEVEL_PLATINUM = "platinum"

    LEVEL_CHOICES = [
        (LEVEL_BRONZE, "Bronze"),
        (LEVEL_SILVER, "Silver"),
        (LEVEL_GOLD, "Gold"),
        (LEVEL_PLATINUM, "Platinum"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_profile",
        help_text="The member this loyalty profile belongs to.",
    )
    points = models.PositiveIntegerField(
        default=0,
        help_text="Current reward point balance.",
    )
    lifetime_spending = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount ever paid by this user across all bookings.",
    )
    total_hours_played = models.PositiveIntegerField(
        default=0,
        help_text="Cumulative hours booked and played.",
    )
    total_bookings = models.PositiveIntegerField(
        default=0,
        help_text="Total number of completed bookings.",
    )
    current_level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        default=LEVEL_BRONZE,
        help_text="Earned loyalty rank, independent of the member's "
        "purchased Membership tier.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-points"]

    def __str__(self):
        return f"{self.user} — {self.get_current_level_display()} ({self.points} pts)"


class MembershipPayment(models.Model):
    """Razorpay payment record for a membership subscription."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"

    subscription = models.OneToOneField(
        MembershipSubscription,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership_payments",
    )
    razorpay_order_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.PositiveIntegerField(help_text="Amount in paise")
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"MembershipPayment #{self.pk} | Sub #{self.subscription_id} | ₹{self.amount_rupees} | {self.status}"

    @property
    def amount_rupees(self):
        from decimal import Decimal
        return (Decimal(self.amount) / Decimal(100)).quantize(Decimal("0.01"))

    @property
    def is_successful(self):
        return self.status in (self.Status.CAPTURED,)
