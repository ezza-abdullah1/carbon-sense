from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmissionData, AreaInfo, LeaderboardEntry


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = ['email', 'name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['email', 'name']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    readonly_fields = ['date_joined', 'last_login']


@admin.register(AreaInfo)
class AreaInfoAdmin(admin.ModelAdmin):
    """Admin configuration for AreaInfo model."""

    list_display = ['id', 'name', 'latitude', 'longitude']
    search_fields = ['id', 'name']
    ordering = ['name']


@admin.register(EmissionData)
class EmissionDataAdmin(admin.ModelAdmin):
    """Admin configuration for EmissionData model."""

    list_display = ['area', 'date', 'total', 'data_type', 'created_at']
    list_filter = ['data_type', 'date', 'area']
    search_fields = ['area__name', 'area__id']
    ordering = ['-date']
    readonly_fields = ['total', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('area', 'date', 'data_type')
        }),
        ('Emission Data by Sector', {
            'fields': ('transport', 'industry', 'energy', 'waste', 'buildings')
        }),
        ('Calculated Fields', {
            'fields': ('total',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    """Admin configuration for LeaderboardEntry model."""

    list_display = ['rank', 'area', 'emissions', 'trend', 'trend_percentage', 'period_start', 'period_end']
    list_filter = ['trend', 'period_start', 'period_end']
    search_fields = ['area__name', 'area__id']
    ordering = ['rank']
