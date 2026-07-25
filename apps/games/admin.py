from django.contrib import admin
from django.utils.html import format_html
from .models import GameConsole, Game


@admin.register(GameConsole)
class GameConsoleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "console_type", "weekday_rate_display",
        "weekend_rate_display", "is_active", "booking_count",
    )
    list_filter = ("console_type", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ()

    @admin.display(description="Weekday Rate")
    def weekday_rate_display(self, obj):
        return f"₹{obj.hourly_rate_weekday}/hr"

    @admin.display(description="Weekend Rate")
    def weekend_rate_display(self, obj):
        return f"₹{obj.hourly_rate_weekend}/hr"

    @admin.display(description="Bookings")
    def booking_count(self, obj):
        return obj.bookings.count()

    actions = ["activate_consoles", "deactivate_consoles"]

    @admin.action(description="Activate selected consoles")
    def activate_consoles(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} console(s) activated.")

    @admin.action(description="Deactivate selected consoles")
    def deactivate_consoles(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} console(s) deactivated.")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "image_preview",
        "rating_display",
        "badge",
        "sort_order",
        "is_active",
    )
    list_filter = ("category", "badge", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("title",)
    readonly_fields = ("created_at", "updated_at", "image_preview_detail")
    ordering = ("sort_order", "title")

    fieldsets = (
        ("Game Info", {
            "description": "Basic details about the game.",
            "fields": ("title", "category"),
        }),
        ("Cover Image", {
            "description": "Upload a cover image OR paste a URL below. Uploaded file takes priority.",
            "fields": ("image", "image_preview_detail", "image_url"),
        }),
        ("Display Settings", {
            "description": "Control how this game appears on the website.",
            "fields": ("badge", "rating", "sort_order"),
        }),
        ("Visibility", {
            "description": "Turn this game on/off on the website.",
            "fields": ("is_active",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Image")
    def image_preview(self, obj):
        src = obj.image_src
        if src:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:6px;" />', src
            )
        return format_html('<span style="color:#888;">No image</span>')

    @admin.display(description="Preview")
    def image_preview_detail(self, obj):
        src = obj.image_src
        if src:
            return format_html(
                '<img src="{}" style="max-width:300px;border-radius:10px;margin-top:8px;" />',
                src,
            )
        return format_html(
            '<span style="color:#888;">No image uploaded yet. Use the field above to upload or paste a URL.</span>'
        )

    @admin.display(description="Rating")
    def rating_display(self, obj):
        return f"{obj.rating}"

    actions = ["activate_games", "deactivate_games"]

    @admin.action(description="Activate selected games")
    def activate_games(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} game(s) activated.")

    @admin.action(description="Deactivate selected games")
    def deactivate_games(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} game(s) deactivated.")
