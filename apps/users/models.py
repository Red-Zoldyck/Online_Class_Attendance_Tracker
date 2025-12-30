"""
User models for the Attendance Tracker.

Models:
- Role: Defines user roles (Admin, Instructor, Student)
- User: Custom user model with extended fields
- UserProfile: Extended user information
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import EmailValidator, URLValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class CustomUserManager(BaseUserManager):
    """Custom manager for the User model."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        logger.info(f"User created: {user.email}")
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # Try to assign Admin role if it exists; otherwise proceed without role
        try:
            admin_role = Role.objects.filter(name=Role.RoleChoices.ADMIN).first()
            if admin_role and 'role' not in extra_fields:
                extra_fields['role'] = admin_role
        except Exception:
            pass
        
        if not extra_fields.get('is_staff'):
            raise ValueError(_('Superuser must have is_staff=True'))
        if not extra_fields.get('is_superuser'):
            raise ValueError(_('Superuser must have is_superuser=True'))
        
        return self.create_user(email, password, **extra_fields)


class Role(models.Model):
    """
    Role model for role-based access control (RBAC).
    
    Roles:
    - Admin: System administrator with full access
    - Instructor: Teacher/Instructor for class management
    - Student: Student accessing class information
    """
    
    class RoleChoices(models.TextChoices):
        """Available role types."""
        ADMIN = 'admin', _('Administrator')
        INSTRUCTOR = 'instructor', _('Instructor')
        STUDENT = 'student', _('Student')
    
    name = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        unique=True,
        db_index=True,
        help_text=_("Role identifier")
    )
    display_name = models.CharField(
        max_length=100,
        help_text=_("Human-readable role name")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of role permissions")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this role is currently active")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.display_name


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    Fields:
    - email: Unique email address for authentication
    - phone_number: Contact phone number
    - role: User's role in the system
    - is_verified: Email verification status
    - profile_picture: User's profile picture
    - last_login_ip: Last login IP address
    """
    
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text=_("User's email address")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("User's phone number")
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        help_text=_("User's assigned role")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Email verification status")
    )
    profile_picture = models.FileField(
        upload_to='profile_pictures/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text=_("User's profile picture")
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address of last login")
    )
    login_attempts = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of failed login attempts")
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Account locked until this timestamp")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def is_account_locked(self):
        """Check if account is currently locked."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False
    
    def reset_login_attempts(self):
        """Reset login attempt counter after successful login."""
        self.login_attempts = 0
        self.locked_until = None
        self.save()
        logger.info(f"Login attempts reset for: {self.email}")
    
    def increment_login_attempts(self):
        """Increment failed login attempts and lock account if needed."""
        self.login_attempts += 1
        if self.login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=30)
            logger.warning(f"Account locked due to multiple failed attempts: {self.email}")
        self.save()


class UserProfile(models.Model):
    """
    Extended user profile with additional information.
    
    Fields:
    - user: OneToOne relationship to User
    - department: User's department/faculty
    - bio: User's biography
    - website: User's website URL
    - social_media: Social media links
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profile',
        help_text=_("Associated user account")
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User's department or faculty")
    )
    bio = models.TextField(
        blank=True,
        help_text=_("User's biography")
    )
    website = models.URLField(
        blank=True,
        validators=[URLValidator()],
        help_text=_("User's website URL")
    )
    social_media = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("User's social media links")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self):
        return f"Profile of {self.user.get_full_name()}"
