"""
Web URL configuration for attendance reports.
"""

from django.urls import path
from apps.reports import views

app_name = 'web-reports'

urlpatterns = [
    path('', views.ReportDashboardView.as_view(), name='dashboard'),
]
