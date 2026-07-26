from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Membership, MembershipSubscription, LoyaltyProfile, MembershipPayment,
)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "name", "price", "included_hours", "weekend_hours",
        "bonus_hours", "duration_days", "is_popular", "is_active",
        "subscriber_count",
    )
    list_editable = ("is_active", "is_popular")
    list_filter = ("is_active", "is_popular", "tier_level")
    search_fields = ("name",)
    ordering = ("tier_level", "price")
    list_per_page = 25
    save_on_top = True

    fieldsets = (
        ("Plan", {
            "fields": (
                "name", "description", "price", "duration_days",
                "is_active", "is_popular", "tier_level",
            ),
        }),
        ("Included Hours", {
            "fields": ("included_hours", "weekend_hours", "bonus_hours"),
        }),
        ("Perks", {
            "fields": ("discount_percent", "priority_booking", "badge_color"),
        }),
    )

    @admin.display(description="Active Subscribers")
    def subscriber_count(self, obj):
        count = obj.subscriptions.filter(status="active").count()
        colour = "#10b981" if count > 0 else "#888"
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            colour, count,
        )

    actions = ["activate_plans", "deactivate_plans"]

    @admin.action(description="Activate selected plans")
    def activate_plans(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} plan(s) activated.")

    @admin.action(description="Deactivate selected plans")
    def deactivate_plans(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} plan(s) deactivated.")


@admin.register(MembershipSubscription)
class MembershipSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user_email", "plan_name", "status_badge",
        "started_at", "expires_at", "days_remaining",
    )
    list_display_links = ("id", "user_email")
    list_filter = ("status",)
    search_fields = ("user__email", "plan__name")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    list_per_page = 25

    @admin.display(description="User")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Plan")
    def plan_name(self, obj):
        return obj.plan.name

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "active": "#10b981",
            "pending": "#f59e0b",
            "expired": "#888",
            "cancelled": "#ef4444",
        }
        colour = colours.get(obj.status, "#888")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            colour, obj.status.title(),
        )

    actions = ["activate_subscriptions", "cancel_subscriptions"]

    @admin.action(description="Activate selected subscriptions")
    def activate_subscriptions(self, request, queryset):
        count = queryset.filter(status="pending").update(status="active")
        self.message_user(request, f"{count} subscription(s) activated.")

    @admin.action(description="Cancel selected subscriptions")
    def cancel_subscriptions(self, request, queryset):
        count = queryset.filter(status="active").update(
            status="cancelled", cancelled_at=timezone.now()
        )
        self.message_user(request, f"{count} subscription(s) cancelled.")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "plan")


@admin.register(LoyaltyProfile)
class LoyaltyProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user_email", "points", "lifetime_spending_display",
        "current_level_badge", "total_bookings", "total_hours_played",
    )
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")
    list_filter = ("current_level",)
    ordering = ("-points",)

    @admin.display(description="User")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Spending")
    def lifetime_spending_display(self, obj):
        return f"\u20b9{obj.lifetime_spending:,.2f}"

    @admin.display(description="Level")
    def current_level_badge(self, obj):
        colours = {
            "bronze": "#cd7f32",
            "silver": "#c0c0c0",
            "gold": "#ffd700",
            "platinum": "#e5e4e2",
        }
        colour = colours.get(obj.current_level, "#888")
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            colour, obj.get_current_level_display(),
        )

    actions = ["recalculate_levels"]

    @admin.action(description="Recalculate loyalty levels for selected profiles")
    def recalculate_levels(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.recalculate_level()
            count += 1
        self.message_user(request, f"{count} profile(s) level recalculated.")


@admin.register(MembershipPayment)
class MembershipPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user_email", "subscription_link",
        "amount_display", "status_badge", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "razorpay_order_id")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="User")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Subscription")
    def subscription_link(self, obj):
        return format_html(
            '<a href="/admin/memberships/membershipsubscription/{}/change/">Sub #{}</a>',
            obj.subscription_id, obj.subscription_id,
        )

    @admin.display(description="Amount")
    def amount_display(self, obj):
        return f"\u20b9{obj.amount_rupees}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "pending": "#f59e0b",
            "captured": "#10b981",
            "failed": "#ef4444",
        }
        colour = colours.get(obj.status, "#888")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            colour, obj.status.title(),
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "subscription")
