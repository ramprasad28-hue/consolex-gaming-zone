from django.db import models
from django.conf import settings


class PaymentQuerySet(models.QuerySet):
    def captured(self):
        return self.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.DEMO])

    def pending(self):
        return self.filter(status=Payment.Status.PENDING)

    def failed(self):
        return self.filter(status=Payment.Status.FAILED)

    def for_user(self, user):
        return self.filter(user=user).select_related("booking")


class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        DEMO = "demo", "Demo Approved"

    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="payment",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
    )
    razorpay_order_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.PositiveIntegerField()  # in paise
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PaymentQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_payment_user_status"),
        ]

    def __str__(self):
        return f"Payment #{self.pk} | Booking #{self.booking_id} | ₹{self.amount_rupees} | {self.status}"

    @property
    def amount_rupees(self):
        from decimal import Decimal
        return (Decimal(self.amount) / Decimal(100)).quantize(Decimal("0.01"))

    @property
    def is_successful(self):
        return self.status in (self.Status.CAPTURED, self.Status.DEMO)
