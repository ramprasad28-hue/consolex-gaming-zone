from django.db import models
from django.conf import settings


class Booking(models.Model):

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    user               = models.ForeignKey(
                             settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             related_name='bookings'
                         )
    game_console       = models.ForeignKey(
                             'games.GameConsole',
                             on_delete=models.SET_NULL,
                             null=True, blank=True,
                             related_name='bookings'
                         )

    booking_date       = models.DateField()
    start_time         = models.TimeField()
    end_time           = models.TimeField()
    number_of_players  = models.PositiveIntegerField(default=1)

    # Stored at booking time so Payment always has a reliable reference
    total_cost         = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    status             = models.CharField(
                             max_length=20,
                             choices=STATUS_CHOICES,
                             default='pending'
                         )

    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-booking_date', '-start_time']

    def __str__(self):
        return (
            f"Booking #{self.id} — {self.user.email} — "
            f"{self.booking_date} {self.start_time}"
        )

    @property
    def duration_hours(self):
        """Returns float hours between start and end time."""
        from datetime import datetime, date
        start = datetime.combine(date.today(), self.start_time)
        end   = datetime.combine(date.today(), self.end_time)
        diff  = (end - start).seconds / 3600
        return round(diff, 2)

    @property
    def advance_amount(self):
        """30% advance — always derived from stored total_cost."""
        return round(self.total_cost * 0.30, 2)

    @property
    def balance_amount(self):
        return round(self.total_cost - self.advance_amount, 2)

    @property
    def is_paid(self):
        return (
            hasattr(self, 'payment') and
            self.payment.status == 'captured'
        )