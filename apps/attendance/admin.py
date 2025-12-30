"""
Admin configuration for Attendance models.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.attendance.models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """Admin interface for AttendanceRecord model."""
    
    list_display = [
        'get_student_name', 'get_session_info', 'status_display',
        'check_in_time', 'check_out_time', 'marked_by', 'marked_at'
    ]
    list_filter = ['status', 'session__class_ref', 'session__date', 'marked_at']
    search_fields = [
        'student__email', 'student__first_name', 'student__last_name',
        'session__class_ref__code', 'notes'
    ]
    readonly_fields = ['marked_at', 'created_at', 'updated_at', 'is_late']
    ordering = ['-marked_at']
    date_hierarchy = 'marked_at'
    
    fieldsets = (
        ('Attendance Information', {
            'fields': ('student', 'session', 'status')
        }),
        ('Check-In/Out', {
            'fields': ('check_in_time', 'check_out_time', 'is_late')
        }),
        ('Notes & Marking', {
            'fields': ('notes', 'marked_by')
        }),
        ('Timestamps', {
            'fields': ('marked_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Display student name."""
        return obj.student.get_full_name()
    get_student_name.short_description = 'Student'
    
    def get_session_info(self, obj):
        """Display session information."""
        return f"{obj.session.class_ref.code} - Session {obj.session.session_number} ({obj.session.date})"
    get_session_info.short_description = 'Session'
    
    def status_display(self, obj):
        """Display attendance status with color."""
        colors = {
            'present': '#28a745',
            'absent': '#dc3545',
            'late': '#ffc107',
            'excused': '#17a2b8',
            'left_early': '#fd7e14'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 5px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Allow adding attendance records only to instructors and admins."""
        return request.user.is_superuser or request.user.role and request.user.role.name in ['instructor', 'admin']
