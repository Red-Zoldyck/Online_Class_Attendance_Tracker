"""
URL configuration for Class web interface.
"""

from django.urls import path
from apps.classes import views

app_name = 'web-classes'

urlpatterns = [
    path('', views.ClassListView.as_view(), name='list'),
    path('<int:pk>/', views.ClassDetailView.as_view(), name='detail'),
]
