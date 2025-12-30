"""
URL configuration for Attendance API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.attendance import views

app_name = 'attendance'

router = DefaultRouter()
router.register(r'records', views.AttendanceRecordViewSet, basename='record')

urlpatterns = [
    path('', include(router.urls)),
]
