"""
URL configuration for Class web interface.
"""

from django.urls import path
from apps.classes import views

app_name = 'web-classes'

urlpatterns = [
    path('', views.ScheduleAssignmentView.as_view(), name='schedule-assignment'),
    path('list/', views.ClassListView.as_view(), name='list'),
    path('section-course/<int:pk>/', views.SectionCourseDetailView.as_view(), name='section-course-detail'),
    path('<int:pk>/', views.ClassDetailView.as_view(), name='detail'),
]
