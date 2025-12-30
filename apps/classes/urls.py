"""
URL configuration for Class API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.classes import views

app_name = 'classes'

router = DefaultRouter()
router.register(r'classes', views.ClassViewSet, basename='class')
router.register(r'sessions', views.SessionViewSet, basename='session')
router.register(r'enrollments', views.StudentEnrollmentViewSet, basename='enrollment')

urlpatterns = [
    path('', include(router.urls)),
]
