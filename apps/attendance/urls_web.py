"""
URL configuration for Attendance web interface.
"""

from django.urls import path
from apps.attendance import views

app_name = 'web-attendance'

urlpatterns = [
    path('session/<int:pk>/', views.SessionAttendanceView.as_view(), name='mark'),
    path('my-records/', views.StudentAttendanceView.as_view(), name='my-records'),
]
