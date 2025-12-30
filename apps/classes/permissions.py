"""
Permissions for class-related API endpoints.
"""

from rest_framework import permissions
from apps.users.models import Role


class IsInstructorOfClass(permissions.BasePermission):
    """Check if user is the instructor of the class."""
    
    message = "Only the class instructor can perform this action."
    
    def has_object_permission(self, request, view, obj):
        return obj.instructor == request.user


class IsEnrolledInClass(permissions.BasePermission):
    """Check if student is enrolled in the class."""
    
    message = "You must be enrolled in this class."
    
    def has_object_permission(self, request, view, obj):
        from apps.classes.models import StudentEnrollment
        return StudentEnrollment.objects.filter(
            student=request.user,
            class_ref=obj,
            is_active=True
        ).exists()


class IsInstructorOrAdmin(permissions.BasePermission):
    """Check if user is instructor or admin."""
    
    message = "Only instructors and administrators can access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role and
            request.user.role.name in [
                Role.RoleChoices.INSTRUCTOR,
                Role.RoleChoices.ADMIN
            ]
        )
