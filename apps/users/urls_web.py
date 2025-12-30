"""
URL configuration for User web interface (templates).
"""

from django.urls import path
from apps.users import views

app_name = 'web-users'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.LoginPageView.as_view(), name='login'),
    path('logout/', views.LogoutPageView.as_view(), name='logout'),
    path('register/', views.RegisterPageView.as_view(), name='register'),
]
