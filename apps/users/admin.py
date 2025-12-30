"""
Admin configuration for User models.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.users.models import User, Role, UserProfile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""
    
    list_display = ['name', 'display_name', 'is_active_display', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Role Information', {
            'fields': ('name', 'display_name', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        """Display active status with color."""
        if obj.is_active:
            return format_html(
                '<span style="color: green;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Inactive</span>'
        )
    is_active_display.short_description = 'Status'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for User model."""
    
    list_display = [
        'email', 'get_full_name', 'role', 'is_verified_display',
        'is_active_display', 'last_login'
    ]
    list_filter = ['role', 'is_active', 'is_verified', 'created_at']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    readonly_fields = ['last_login', 'created_at', 'updated_at', 'last_login_ip']
    ordering = ['-created_at']
    filter_horizontal = ['groups', 'user_permissions']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('email', 'username', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Role & Permissions', {
            'fields': ('role', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': ('is_active', 'is_verified')
        }),
        ('Security', {
            'fields': ('last_login', 'last_login_ip', 'login_attempts', 'locked_until'),
            'classes': ('collapse',)
        }),
        ('Profile Picture', {
            'fields': ('profile_picture',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        """Display user's full name."""
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    
    def is_verified_display(self, obj):
        """Display email verification status."""
        if obj.is_verified:
            return format_html(
                '<span style="color: green;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Unverified</span>'
        )
    is_verified_display.short_description = 'Email Status'
    
    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html(
                '<span style="color: green;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Inactive</span>'
        )
    is_active_display.short_description = 'Account Status'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model."""
    
    list_display = ['get_user_email', 'department', 'created_at']
    list_filter = ['department', 'created_at']
    search_fields = ['user__email', 'department', 'bio']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Profile Information', {
            'fields': ('department', 'bio', 'website')
        }),
        ('Social Media', {
            'fields': ('social_media',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_user_email(self, obj):
        """Display user email."""
        return obj.user.email
    get_user_email.short_description = 'User Email'
