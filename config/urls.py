"""
URL Configuration for attendance_tracker project.

The `urlpatterns` list routes URLs to views and APIs.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions, routers

# API Documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Attendance Tracker API",
        default_version='v1',
        description="Online Class Attendance Tracker API Documentation",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="support@attendancetracker.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin Interface
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/v1/docs/swagger/', schema_view.with_ui('swagger', cache_timeout=0), 
         name='schema-swagger-ui'),
    path('api/v1/docs/redoc/', schema_view.with_ui('redoc', cache_timeout=0), 
         name='schema-redoc'),
    
    # Apps URLs
    path('api/v1/', include('apps.users.urls', namespace='users')),
    path('api/v1/', include('apps.classes.urls', namespace='classes')),
    path('api/v1/', include('apps.attendance.urls', namespace='attendance')),
    path('api/v1/', include('apps.reports.urls', namespace='reports')),
    
    # Web Interface URLs
    path('', include('apps.users.urls_web', namespace='web-users')),
    path('classes/', include('apps.classes.urls_web', namespace='web-classes')),
    path('attendance/', include('apps.attendance.urls_web', namespace='web-attendance')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Error Handlers
handler404 = 'apps.users.views.page_not_found'
handler500 = 'apps.users.views.server_error'
