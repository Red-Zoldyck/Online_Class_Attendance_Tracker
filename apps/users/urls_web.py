"""
URL configuration for User web interface (templates).
"""

from django.urls import path
from apps.users import views

app_name = 'web-users'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.LoginPageView.as_view(), name='login'),
    path('logout/', views.logout_redirect, name='logout'),
    path('register/', views.RegisterPageView.as_view(), name='register'),
    path('management/academics/', views.AdminAcademicsView.as_view(), name='admin-academics'),
    path('management/students/', views.AdminStudentListView.as_view(), name='admin-students'),
    path('management/instructor-applications/', views.InstructorApplicationsAdminView.as_view(), name='admin-instructor-applications'),
    path('instructor/apply/', views.InstructorApplicationView.as_view(), name='instructor-apply'),
    path('profile/', views.ProfilePageView.as_view(), name='profile'),
]
