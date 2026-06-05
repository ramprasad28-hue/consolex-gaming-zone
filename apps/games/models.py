from django.db import models

class GameConsole(models.Model):
    CONSOLE_TYPES = [
        ('PS5', 'PlayStation 5'),
        ('PS4', 'PlayStation 4'),
        ('XBOX', 'Xbox Series X'),
    ]

    name = models.CharField(max_length=100)
    console_type = models.CharField(max_length=10, choices=CONSOLE_TYPES)
    hourly_rate_weekday = models.DecimalField(max_digits=6, decimal_places=2)
    hourly_rate_weekend = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='consoles/', blank=True, null=True)

    def __str__(self):
        return self.name