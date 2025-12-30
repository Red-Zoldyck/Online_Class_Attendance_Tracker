"""
Attendance app configuration.
"""

from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    """Configuration for the Attendance application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.attendance'
    verbose_name = 'Attendance Tracking'
