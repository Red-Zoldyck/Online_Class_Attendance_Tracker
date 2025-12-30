"""
Admin configuration for Class models.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.classes.models import Class, Session, StudentEnrollment


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """Admin interface for Class model."""
    
    list_display = [
        'code', 'name', 'get_instructor_name', 'enrolled_count',
        'capacity', 'is_active_display', 'start_date'
    ]
    list_filter = ['is_active', 'instructor', 'start_date', 'created_at']
    search_fields = ['code', 'name', 'description', 'instructor__email']
    readonly_fields = ['created_at', 'updated_at', 'enrolled_count', 'available_slots']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Class Information', {
            'fields': ('code', 'name', 'description', 'instructor')
        }),
        ('Schedule & Capacity', {
            'fields': ('start_date', 'end_date', 'schedule', 'capacity', 'enrolled_count', 'available_slots')
        }),
        ('Platform', {
            'fields': ('platform_url',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_instructor_name(self, obj):
        """Display instructor name."""
        return obj.instructor.get_full_name()
    get_instructor_name.short_description = 'Instructor'
    
    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Status'


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin interface for Session model."""
    
    list_display = [
        'get_class_code', 'session_number', 'date', 'start_time',
        'end_time', 'topic', 'is_held_display'
    ]
    list_filter = ['is_held', 'class_ref', 'date', 'created_at']
    search_fields = ['class_ref__code', 'topic', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date', '-start_time']
    
    fieldsets = (
        ('Class & Session', {
            'fields': ('class_ref', 'session_number')
        }),
        ('Schedule', {
            'fields': ('date', 'start_time', 'end_time')
        }),
        ('Content', {
            'fields': ('topic', 'notes')
        }),
        ('Status', {
            'fields': ('is_held',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_class_code(self, obj):
        """Display class code."""
        return obj.class_ref.code
    get_class_code.short_description = 'Class Code'
    
    def is_held_display(self, obj):
        """Display session held status."""
        if obj.is_held:
            return format_html('<span style="color: green;">✓ Held</span>')
        return format_html('<span style="color: red;">✗ Not Held</span>')
    is_held_display.short_description = 'Session Held'


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    """Admin interface for StudentEnrollment model."""
    
    list_display = [
        'get_student_name', 'get_class_code', 'enrollment_date',
        'is_active_display', 'created_at'
    ]
    list_filter = ['class_ref', 'is_active', 'enrollment_date', 'created_at']
    search_fields = ['student__email', 'student__first_name', 'student__last_name', 'class_ref__code']
    readonly_fields = ['enrollment_date', 'created_at', 'updated_at']
    ordering = ['-enrollment_date']
    
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('student', 'class_ref', 'enrollment_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Display student name."""
        return obj.student.get_full_name()
    get_student_name.short_description = 'Student'
    
    def get_class_code(self, obj):
        """Display class code."""
        return obj.class_ref.code
    get_class_code.short_description = 'Class'
    
    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Status'
