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
            'phone_number', 'role', 'role_id', 'is_verified',
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
            'is_verified', 'is_active', 'profile_picture',
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
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name',
            'password', 'password_confirm', 'phone_number', 'role'
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
        """Validate that passwords match."""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({'password': "Passwords do not match."})
        return data
    
    def create(self, validated_data):
        """Create a new user with validated data."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
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
