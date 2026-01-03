"""
Serializers for User models.

DRF serializers for API endpoints:
- UserSerializer: Basic user information
- UserDetailSerializer: Complete user information
- UserRegistrationSerializer: User registration
- ChangePasswordSerializer: Password change functionality
"""

from rest_framework import serializers
from apps.users.models import User, Role, UserProfile
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'display_name', 'description', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    
    class Meta:
        model = UserProfile
        fields = ['department', 'bio', 'website', 'social_media']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    Used for listing and retrieving user information.
    """
    
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Role.objects.all(),
        source='role',
        required=False
    )
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone_number', 'student_number', 'role', 'role_id', 'is_verified',
            'is_active', 'last_login', 'created_at', 'profile'
        ]
        read_only_fields = [
            'id', 'created_at', 'last_login', 'is_verified'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for User model.
    Includes all user information including sensitive fields.
    """
    
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Role.objects.all(),
        source='role',
        required=False
    )
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'phone_number', 'role', 'role_id',
            'student_number', 'is_verified', 'is_active', 'profile_picture',
            'last_login', 'created_at', 'updated_at', 'profile'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_login', 'is_verified'
        ]
    
    def get_full_name(self, obj):
        """Get user's full name."""
        return obj.get_full_name()
    
    def update(self, instance, validated_data):
        """Update user information."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"User updated: {instance.email}")
        return instance


class SelfProfileSerializer(serializers.ModelSerializer):
    """Serializer for self-service profile updates with protected identifiers."""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'profile_picture'
        ]
        read_only_fields = []

    def validate(self, attrs):
        user: User = self.instance  # type: ignore
        role_name = getattr(getattr(user, 'role', None), 'name', None)

        # Students must not change email to another student's number? Keep email change allowed but student_number blocked elsewhere.
        if role_name == Role.RoleChoices.STUDENT:
            # explicit guard: student_number is immutable via serializer by omission
            pass
        if role_name == Role.RoleChoices.INSTRUCTOR:
            # instructor id (if stored in username/student_number) is also protected by omission
            pass
        return attrs


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Handles password validation and user creation.
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="At least 8 characters with uppercase, lowercase, and numbers"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirm password"
    )
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.filter(is_active=True),
        help_text="User's role in the system"
    )
    student_number = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="For students: format 04141-YY-XXXX"
    )
    teacher_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="For instructors: school-issued teacher ID"
    )
    admin_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Admin creation code"
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name',
            'password', 'password_confirm', 'phone_number', 'role',
            'student_number', 'teacher_id', 'admin_code'
        ]
    
    def validate_email(self, value):
        """Validate that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value
    
    def validate_username(self, value):
        """Validate that username is unique."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value
    
    def validate_password(self, value):
        """Validate password strength."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def validate(self, data):
        """Validate that passwords match and role-specific codes are provided."""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({'password': "Passwords do not match."})

        role = data.get('role')
        if role:
            role_name = role.name
            if role_name == Role.RoleChoices.STUDENT:
                sn = (data.get('student_number') or '').strip()
                import re
                if not sn or not re.fullmatch(r"04141-\d{2}-\d{4}", sn):
                    raise serializers.ValidationError({'student_number': "Student number must match 04141-YY-XXXX."})
            elif role_name == Role.RoleChoices.INSTRUCTOR:
                tid = (data.get('teacher_id') or '').strip()
                if not tid:
                    raise serializers.ValidationError({'teacher_id': "Teacher ID is required for instructors."})
            elif role_name == Role.RoleChoices.ADMIN:
                code = (data.get('admin_code') or '').strip()
                if code != "@dm|n@2o2G!":
                    raise serializers.ValidationError({'admin_code': "Invalid admin code."})
        return data
    
    def create(self, validated_data):
        """Create a new user with validated data."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        student_number = validated_data.pop('student_number', None)
        validated_data.pop('teacher_id', None)
        validated_data.pop('admin_code', None)

        user = User.objects.create_user(password=password, **validated_data)
        if student_number:
            user.student_number = student_number
            user.save(update_fields=['student_number'])
        logger.info(f"New user registered: {user.email}")
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    """
    
    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate_new_password(self, value):
        """Validate new password strength."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def validate(self, data):
        """Validate that new passwords match."""
        if data.get('new_password') != data.get('new_password_confirm'):
            raise serializers.ValidationError({'new_password': "Passwords do not match."})
        return data
    
    def validate_old_password(self, value):
        """Validate that old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
