from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "booking_link", "user_email",
        "amount_display", "status_badge", "mode_badge", "created_at",
    )
    list_display_links = ("id", "booking_link")
    list_filter = ("status", "is_demo", "currency")
    search_fields = ("razorpay_order_id", "razorpay_payment_id", "user__email")
    readonly_fields = (
        "razorpay_order_id", "razorpay_payment_id",
        "razorpay_signature", "created_at", "updated_at",
    )
    ordering = ("-created_at",)
    list_per_page = 25
    save_on_top = True

    @admin.display(description="Booking")
    def booking_link(self, obj):
        return format_html(
            '<a href="/admin/bookings/booking/{}/change/">Booking #{}</a>',
            obj.booking_id, obj.booking_id,
        )

    @admin.display(description="Customer")
    def user_email(self, obj):
        return obj.user.email if obj.user else "—"

    @admin.display(description="Amount")
    def amount_display(self, obj):
        return f"\u20b9{obj.amount_rupees}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "pending": "#f59e0b",
            "demo": "#6366f1",
            "captured": "#10b981",
            "failed": "#ef4444",
            "refunded": "#64748b",
        }
        colour = colours.get(obj.status, "#888")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            colour, obj.get_status_display(),
        )

    @admin.display(description="Mode")
    def mode_badge(self, obj):
        if obj.is_demo:
            return format_html(
                '<span style="background:#7c3aed;color:#fff;padding:2px 8px;'
                'border-radius:8px;font-size:11px;">{}</span>', "DEMO"
            )
        return format_html(
            '<span style="background:#0f766e;color:#fff;padding:2px 8px;'
            'border-radius:8px;font-size:11px;">{}</span>', "LIVE"
        )

    actions = ["mark_as_refunded"]

    @admin.action(description="Mark selected payments as refunded")
    def mark_as_refunded(self, request, queryset):
        count = queryset.filter(status__in=["captured", "demo"]).update(status="refunded")
        self.message_user(request, f"{count} payment(s) marked as refunded.")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "booking")


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = (
        "razorpay_order_id", "razorpay_payment_id",
        "amount", "status", "is_demo", "created_at",
    )
    fields = (
        "razorpay_order_id", "razorpay_payment_id",
        "amount", "status", "is_demo",
    )
