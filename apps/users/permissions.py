"""
Permissions for user-related API endpoints.
"""

from rest_framework import permissions
from apps.users.models import Role


class IsAdmin(permissions.BasePermission):
    """Permission to check if user is admin."""
    
    message = "Only administrators can access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role and
            request.user.role.name == Role.RoleChoices.ADMIN
        )


class IsInstructor(permissions.BasePermission):
    """Permission to check if user is instructor."""
    
    message = "Only instructors can access this resource."
    
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


class IsStudent(permissions.BasePermission):
    """Permission to check if user is student."""
    
    message = "Only students can access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role and
            request.user.role.name == Role.RoleChoices.STUDENT
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow admin full access, others get read-only access.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role and
            request.user.role.name == Role.RoleChoices.ADMIN
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow owners or admin to access their own resources.
    """
    
    message = "You can only access your own information or be an administrator."
    
    def has_object_permission(self, request, view, obj):
        from apps.users.models import User
        if isinstance(obj, User):
            return (
                obj == request.user or
                (request.user.role and 
                 request.user.role.name == Role.RoleChoices.ADMIN)
            )
        return False
