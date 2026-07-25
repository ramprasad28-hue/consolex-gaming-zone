from django.contrib import admin
from django.utils.html import format_html
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user_email", "game_console", "booking_date",
        "start_time", "end_time", "players", "total_cost_display",
        "advance_display", "status_badge", "payment_status", "created_at",
    )
    list_filter = ("status", "booking_date", "game_console")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("total_cost", "created_at", "updated_at")
    ordering = ("-booking_date", "-start_time")
    date_hierarchy = "booking_date"

    @admin.display(description="Customer")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Players")
    def players(self, obj):
        return obj.number_of_players

    @admin.display(description="Total")
    def total_cost_display(self, obj):
        return f"\u20b9{obj.total_cost}"

    @admin.display(description="Advance")
    def advance_display(self, obj):
        return f"\u20b9{obj.advance_amount}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "pending": "#f59e0b",
            "confirmed": "#10b981",
            "cancelled": "#ef4444",
            "completed": "#6366f1",
        }
        colour = colours.get(obj.status, "#888")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.display(description="Payment")
    def payment_status(self, obj):
        if hasattr(obj, "payment"):
            p = obj.payment
            if p.status == "captured":
                return format_html(
                    '<span style="color:#10b981;font-weight:600;">\u2705 Paid \u20b9{}</span>',
                    p.amount_rupees,
                )
            if p.status == "demo":
                return format_html(
                    '<span style="color:#6366f1;font-weight:600;">\U0001f680 Demo \u20b9{}</span>',
                    p.amount_rupees,
                )
            return format_html(
                '<span style="color:#f59e0b;">{}</span>', p.status.title()
            )
        return format_html('<span style="color:#888;">No payment</span>')

    actions = ["mark_confirmed", "mark_completed", "mark_cancelled"]

    @admin.action(description="Mark selected bookings as confirmed")
    def mark_confirmed(self, request, queryset):
        count = queryset.filter(status="pending").update(status="confirmed")
        self.message_user(request, f"{count} booking(s) confirmed.")

    @admin.action(description="Mark selected bookings as completed")
    def mark_completed(self, request, queryset):
        count = queryset.filter(status="confirmed").update(status="completed")
        self.message_user(request, f"{count} booking(s) marked completed.")

    @admin.action(description="Cancel selected bookings")
    def mark_cancelled(self, request, queryset):
        count = queryset.filter(status__in=["pending", "confirmed"]).update(status="cancelled")
        self.message_user(request, f"{count} booking(s) cancelled.")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "game_console", "payment")
