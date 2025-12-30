"""
Celery configuration for attendance_tracker project.
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('attendance_tracker')

# Load configuration from Django settings using CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
