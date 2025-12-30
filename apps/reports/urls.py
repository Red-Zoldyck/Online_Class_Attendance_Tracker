"""
URL configuration for Reports API endpoints.
"""

from django.urls import path
from apps.reports import views

app_name = 'reports'

urlpatterns = [
    path('class-report/', views.ClassAttendanceReportView.as_view(), name='class-report'),
    path('student-report/', views.StudentAttendanceReportView.as_view(), name='student-report'),
    path('export/', views.ExportReportView.as_view(), name='export'),
]
