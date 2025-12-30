"""
Classes app configuration.
"""

from django.apps import AppConfig


class ClassesConfig(AppConfig):
    """Configuration for the Classes application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.classes'
    verbose_name = 'Class Management'
