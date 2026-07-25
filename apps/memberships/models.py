from django.conf import settings
from django.db import models
from django.utils import timezone


class MembershipQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def by_tier(self, tier_level):
        return self.filter(tier_level__gte=tier_level)


class Membership(models.Model):
    """Master catalog of purchasable membership plans."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(
        help_text="Membership validity in days",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate to retire a plan without deleting its history.",
    )
    discount_percent = models.PositiveIntegerField(
        default=0,
        help_text="Booking discount (0-100).",
    )
    priority_booking = models.BooleanField(default=False)
    free_hours_per_month = models.PositiveIntegerField(default=0)
    included_hours = models.PositiveIntegerField(default=0)
    weekend_hours = models.PositiveIntegerField(default=0)
    bonus_hours = models.PositiveIntegerField(default=0)
    badge_color = models.CharField(max_length=7, blank=True)
    tier_level = models.PositiveIntegerField(default=0)
    is_popular = models.BooleanField(default=False)

    objects = MembershipQuerySet.as_manager()

    class Meta:
        ordering = ["tier_level", "price"]

    def __str__(self):
        return self.name

    @property
    def total_hours(self):
        return self.included_hours + self.weekend_hours + self.bonus_hours


class SubscriptionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            status=MembershipSubscription.STATUS_ACTIVE,
            expires_at__gt=timezone.now(),
        )

    def for_user(self, user):
        return self.filter(user=user).select_related("plan")


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
    )
    plan = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    auto_renew = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SubscriptionQuerySet.as_manager()

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="unique_active_subscription_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_sub_user_status"),
            models.Index(fields=["status", "expires_at"], name="idx_sub_status_expiry"),
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


class LoyaltyProfileQuerySet(models.QuerySet):
    def by_level(self, level):
        return self.filter(current_level=level)

    def top_spenders(self, limit=10):
        return self.order_by("-lifetime_spending")[:limit]


class LoyaltyProfile(models.Model):
    """Always-one-row-per-user rollup of a member's activity."""

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

    LEVEL_THRESHOLDS = {
        LEVEL_BRONZE: 0,
        LEVEL_SILVER: 500,
        LEVEL_GOLD: 2000,
        LEVEL_PLATINUM: 5000,
    }

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_profile",
    )
    points = models.PositiveIntegerField(default=0)
    lifetime_spending = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_hours_played = models.PositiveIntegerField(default=0)
    total_bookings = models.PositiveIntegerField(default=0)
    current_level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        default=LEVEL_BRONZE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LoyaltyProfileQuerySet.as_manager()

    class Meta:
        ordering = ["-points"]
        indexes = [
            models.Index(fields=["current_level"], name="idx_loyalty_level"),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_current_level_display()} ({self.points} pts)"

    def recalculate_level(self):
        """Determine level based on lifetime spending."""
        for level, threshold in sorted(
            self.LEVEL_THRESHOLDS.items(), key=lambda x: x[1], reverse=True
        ):
            if self.lifetime_spending >= threshold:
                if self.current_level != level:
                    self.current_level = level
                    self.save(update_fields=["current_level", "updated_at"])
                return level
        return self.current_level


class MembershipPaymentQuerySet(models.QuerySet):
    def captured(self):
        return self.filter(status=MembershipPayment.Status.CAPTURED)

    def pending(self):
        return self.filter(status=MembershipPayment.Status.PENDING)


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
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MembershipPaymentQuerySet.as_manager()

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
