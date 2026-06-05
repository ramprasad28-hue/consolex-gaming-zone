from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'console', 'date', 'start_time', 'end_time', 'number_of_players', 'total_cost', 'status')
    list_filter = ('status', 'date', 'console')
    search_fields = ('user__email', 'console__name')
    ordering = ('-date', '-start_time')
    list_editable = ('status',)
