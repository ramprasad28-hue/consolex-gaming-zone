# ─────────────────────────────────────────────
# File: apps/payments/models.py
# ─────────────────────────────────────────────

from django.db import models
from django.conf import settings
from apps.bookings.models import Booking


class Payment(models.Model):

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('demo',     'Demo Approved'),   # ← demo mode
        ('captured', 'Captured'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ]

    booking             = models.OneToOneField(
                              Booking,
                              on_delete=models.CASCADE,
                              related_name='payment'
                          )
    user                = models.ForeignKey(
                              settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name='payments',
                              null=True,
                              blank=True
                          )

    # Razorpay identifiers — blank in demo mode
    razorpay_order_id   = models.CharField(max_length=100, blank=True, default='')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature  = models.CharField(max_length=255, blank=True, null=True)

    # Amount in paise
    amount        = models.PositiveIntegerField(
                              help_text='Amount in paise (₹1 = 100 paise)'
                          )
    currency            = models.CharField(max_length=10, default='INR')
    status              = models.CharField(
                              max_length=20,
                              choices=STATUS_CHOICES,
                              default='pending'
                          )

    # Marks whether this was processed in demo mode
    is_demo             = models.BooleanField(default=False)

    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        mode = ' [DEMO]' if self.is_demo else ''
        return (
            f"Payment #{self.id}{mode} — "
            f"Booking #{self.booking_id} — "
            f"₹{self.amount_rupees} — {self.status}"
        )

    @property
    def amount_rupees(self):
        return round(self.amount / 100, 2)