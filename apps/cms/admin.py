from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SiteSettings, ContentBlock, Announcement, Testimonial,
    SiteStat, Feature, FAQItem, GalleryItem,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Brand", {
            "fields": ["brand_name", "tagline"],
        }),
        ("Contact", {
            "fields": ["phone", "address", "operating_hours"],
        }),
        ("Social Links", {
            "fields": [
                "whatsapp_number", "instagram_handle", "instagram_url",
                "instagram_follower_count", "google_review_url",
                "google_rating", "google_review_count",
            ],
        }),
        ("SEO / Meta", {
            "fields": ["meta_description", "og_title", "og_description"],
        }),
        ("Theme", {
            "fields": ["theme_color", "theme_color_light"],
        }),
        ("Dashboard", {
            "fields": ["dashboard_hero_image"],
        }),
    ]

    def has_add_permission(self, request):
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.objects.get_solo()
        return admin.ModelAdmin.changelist_view(self, request, extra_context=extra_context)


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ["key", "value_preview", "updated_at"]
    search_fields = ["key", "value"]
    ordering = ["key"]

    def value_preview(self, obj):
        return obj.value[:80] + "…" if len(obj.value) > 80 else obj.value
    value_preview.short_description = "Value"


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["text_preview", "is_active", "cta_text"]
    list_editable = ["is_active"]

    def text_preview(self, obj):
        return obj.text[:60] + "…" if len(obj.text) > 60 else obj.text
    text_preview.short_description = "Text"


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["name", "role", "game_tag", "rating", "is_active", "sort_order"]
    list_editable = ["is_active", "sort_order", "rating"]
    list_filter = ["is_active"]


@admin.register(SiteStat)
class SiteStatAdmin(admin.ModelAdmin):
    list_display = ["__str__", "sort_order"]
    list_editable = ["sort_order"]


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ["title", "section", "image_preview", "sort_order"]
    list_editable = ["sort_order"]
    list_filter = ["section"]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="40" />', obj.image.url)
        return "—"
    image_preview.short_description = "Image"


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ["question_preview", "category", "sort_order"]
    list_editable = ["sort_order"]
    list_filter = ["category"]

    def question_preview(self, obj):
        return obj.question[:70] + "…" if len(obj.question) > 70 else obj.question
    question_preview.short_description = "Question"


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ["caption", "image_preview", "sort_order"]
    list_editable = ["sort_order"]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="40" />', obj.image.url)
        return "—"
    image_preview.short_description = "Image"
