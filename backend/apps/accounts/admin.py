from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'display_name', 'google_id', 'is_staff', 'date_joined')
    search_fields = ('email', 'display_name', 'google_id')
    readonly_fields = ('google_id', 'avatar_url', 'date_joined', 'last_login')
    fieldsets = (
        (None, {'fields': ('email', 'google_id', 'display_name', 'avatar_url')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'google_id', 'display_name')}),
    )
    ordering = ('-date_joined',)
