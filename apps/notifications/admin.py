from django.contrib import admin
from django.utils.html import format_html
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user_email", "message_truncated", "is_read_badge", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__email", "message")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25

    @admin.display(description="User")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Message")
    def message_truncated(self, obj):
        if len(obj.message) > 80:
            return obj.message[:80] + "..."
        return obj.message

    @admin.display(description="Read")
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color:#10b981;font-weight:600;">{}</span>', "\u2713 Read"
            )
        return format_html(
            '<span style="color:#f59e0b;font-weight:600;">{}</span>', "\u25cf Unread"
        )

    actions = ["mark_all_read", "mark_all_unread"]

    @admin.action(description="Mark selected notifications as read")
    def mark_all_read(self, request, queryset):
        count = queryset.filter(is_read=False).update(is_read=True)
        self.message_user(request, f"{count} notification(s) marked as read.")

    @admin.action(description="Mark selected notifications as unread")
    def mark_all_unread(self, request, queryset):
        count = queryset.filter(is_read=True).update(is_read=False)
        self.message_user(request, f"{count} notification(s) marked as unread.")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
