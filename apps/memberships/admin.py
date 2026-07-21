from django.contrib import admin
from .models import Membership, MembershipSubscription, LoyaltyProfile, MembershipPayment


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


@admin.register(MembershipSubscription)
class MembershipSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'status', 'started_at', 'expires_at', 'days_remaining')
    list_filter = ('status',)
    search_fields = ('user__email', 'plan__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LoyaltyProfile)
class LoyaltyProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'lifetime_spending', 'current_level', 'total_bookings')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MembershipPayment)
class MembershipPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subscription', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'razorpay_order_id')
    readonly_fields = ('created_at', 'updated_at')
