"""
Users app configuration.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for the Users application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'User Management'
