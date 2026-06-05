from django.db import models

class Membership(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(help_text="Membership validity in days")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name