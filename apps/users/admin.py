from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'phone', 'is_verified', 'membership', 'date_joined')
    list_filter = ('is_verified', 'membership', 'is_staff')
    search_fields = ('email', 'username', 'phone')
    ordering = ('-date_joined',)
    fieldsets = UserAdmin.fieldsets + (
        ('CONSOLEX Info', {'fields': ('phone', 'is_verified', 'membership')}),
    )
