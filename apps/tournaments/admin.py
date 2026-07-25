from django.contrib import admin
from django.utils.html import format_html
from .models import Tournament


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "game",
        "image_preview",
        "date_display",
        "prize_display",
        "slots_display",
        "status",
        "is_active",
    )
    list_filter = ("status", "is_active")
    list_editable = ("is_active",)
    search_fields = ("title", "game")
    readonly_fields = ("created_at", "updated_at", "image_preview_detail")
    ordering = ("date",)

    fieldsets = (
        ("Tournament Info", {
            "description": "Name, game, and description of the tournament.",
            "fields": ("title", "game", "description"),
        }),
        ("Schedule & Slots", {
            "description": "When is it and how many players can join?",
            "fields": ("date", "total_slots", "registered_slots"),
        }),
        ("Prize & Status", {
            "description": "Prize pool amount and current tournament status.",
            "fields": ("prize_pool", "status"),
        }),
        ("Banner Image", {
            "description": "Upload a banner image OR paste a URL below. Uploaded file takes priority.",
            "fields": ("image", "image_preview_detail", "image_url"),
        }),
        ("Visibility", {
            "description": "Show or hide this tournament on the website.",
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
        return format_html('<span style="color:#888;">{}</span>', "No image")

    @admin.display(description="Preview")
    def image_preview_detail(self, obj):
        src = obj.image_src
        if src:
            return format_html(
                '<img src="{}" style="max-width:400px;border-radius:10px;margin-top:8px;" />',
                src,
            )
        return format_html(
            '<span style="color:#888;">{}</span>',
            "No image uploaded yet. Use the field above to upload or paste a URL.",
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
