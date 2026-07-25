from django.contrib import admin
from django.utils.html import format_html
from .models import Tournament


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "game",
        "date_display",
        "prize_display",
        "slots_display",
        "status",
        "is_active",
    )
    list_filter = ("status", "is_active")
    list_editable = ("is_active",)
    search_fields = ("title", "game")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("date",)

    fieldsets = (
        (None, {
            "fields": ("title", "game", "description"),
        }),
        ("Schedule & Slots", {
            "fields": ("date", "total_slots", "registered_slots"),
        }),
        ("Prize & Status", {
            "fields": ("prize_pool", "status"),
        }),
        ("Media", {
            "fields": ("image_url",),
        }),
        ("Visibility", {
            "fields": ("is_active",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Date")
    def date_display(self, obj):
        return obj.date.strftime("%b %d, %Y  %I:%M %p")

    @admin.display(description="Prize Pool")
    def prize_display(self, obj):
        return f"₹{obj.prize_pool:,.0f}"

    @admin.display(description="Slots")
    def slots_display(self, obj):
        return f"{obj.registered_slots}/{obj.total_slots}"

    actions = ["activate_tournaments", "deactivate_tournaments"]

    @admin.action(description="Activate selected tournaments")
    def activate_tournaments(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} tournament(s) activated.")

    @admin.action(description="Deactivate selected tournaments")
    def deactivate_tournaments(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} tournament(s) deactivated.")
