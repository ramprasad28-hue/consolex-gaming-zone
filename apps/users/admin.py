from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "email", "username", "phone", "is_verified",
        "membership_display", "is_staff", "date_joined",
    )
    list_filter = ("is_verified", "is_staff", "membership", "is_active")
    search_fields = ("email", "username", "phone", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login")

    fieldsets = UserAdmin.fieldsets + (
        ("CONSOLEX Info", {
            "fields": ("phone", "is_verified", "membership"),
        }),
    )

    @admin.display(description="Membership")
    def membership_display(self, obj):
        if obj.membership:
            return format_html(
                '<span style="color:{};font-weight:600;">{}</span>',
                obj.membership.badge_color or "#888",
                obj.membership.name,
            )
        return format_html('<span style="color:#888;">None</span>')

    actions = ["verify_users", "unverify_users"]

    @admin.action(description="Mark selected users as verified")
    def verify_users(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} user(s) marked as verified.")

    @admin.action(description="Unverify selected users")
    def unverify_users(self, request, queryset):
        count = queryset.update(is_verified=False)
        self.message_user(request, f"{count} user(s) unverified.")
