from django.contrib import admin
from .models import Membership


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'price', 'included_hours', 'weekend_hours',
        'bonus_hours', 'duration_days', 'is_popular', 'is_active',
    )
    list_editable = ('is_active', 'is_popular')
    list_filter = ('is_active', 'is_popular', 'tier_level')
    search_fields = ('name',)
    ordering = ('tier_level', 'price')

    fieldsets = (
        ("Plan", {
            "fields": (
                'name', 'description', 'price', 'duration_days',
                'is_active', 'is_popular', 'tier_level',
            ),
        }),
        ("Included Hours", {
            "fields": ('included_hours', 'weekend_hours', 'bonus_hours'),
        }),
        ("Perks", {
            "fields": ('discount_percent', 'priority_booking', 'badge_color'),
        }),
    )
