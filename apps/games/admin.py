from django.contrib import admin
from .models import GameConsole

@admin.register(GameConsole)
class GameConsoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'console_type', 'hourly_rate_weekday', 'hourly_rate_weekend', 'is_active')
    list_filter = ('console_type', 'is_active')
    list_editable = ('is_active',)
