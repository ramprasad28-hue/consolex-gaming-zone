from django.db import models
from apps.bookings.models import Booking
from django.db import models
from django.conf import settings
from apps.bookings.models import Booking


class Payment(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.razorpay_order_id} – {self.status}"

class Payment(models.Model):

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('captured',  'Captured'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    booking             = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)

    # Razorpay identifiers
    razorpay_order_id   = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature  = models.CharField(max_length=255, blank=True, null=True)

    # Amount in paise (Razorpay uses smallest currency unit)
    amount        = models.PositiveIntegerField(help_text='Amount in paise (₹1 = 100 paise)')
    currency            = models.CharField(max_length=10, default='INR')
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} — {self.booking} — ₹{self.amount // 100} — {self.status}"

    @property
    def amount_rupees(self):
        return self.amount / 100