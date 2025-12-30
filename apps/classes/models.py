"""
Class and Session models for the Attendance Tracker.

Models:
- Class: Online class information
- Session: Individual class session
- StudentEnrollment: Student enrollment in a class
"""

from django.db import models
from django.core.validators import URLValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)


class Class(models.Model):
    """
    Class model representing an online class.
    
    Fields:
    - code: Unique class code (e.g., CS101)
    - name: Class name
    - description: Detailed description
    - instructor: Instructor teaching the class
    - capacity: Maximum number of students
    - schedule: Class meeting schedule
    - platform_url: Link to class platform
    - is_active: Whether class is currently active
    - start_date: Class start date
    - end_date: Class end date
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Unique class code")
    )
    name = models.CharField(
        max_length=200,
        help_text=_("Class name")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed class description")
    )
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='taught_classes',
        help_text=_("Instructor for this class")
    )
    capacity = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        help_text=_("Maximum number of students")
    )
    schedule = models.CharField(
        max_length=200,
        help_text=_("Class schedule (e.g., Mon/Wed 10:00 AM)")
    )
    platform_url = models.URLField(
        blank=True,
        validators=[URLValidator()],
        help_text=_("Link to class platform or meeting")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether class is currently active")
    )
    start_date = models.DateField(
        help_text=_("Class start date")
    )
    end_date = models.DateField(
        help_text=_("Class end date")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Class')
        verbose_name_plural = _('Classes')
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['instructor']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def enrolled_count(self):
        """Get number of enrolled students."""
        return self.students.filter(is_active=True).count()
    
    @property
    def available_slots(self):
        """Get number of available enrollment slots."""
        return max(0, self.capacity - self.enrolled_count)
    
    @property
    def is_ongoing(self):
        """Check if class is currently ongoing."""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date and self.is_active


class Session(models.Model):
    """
    Session model representing individual class sessions.
    
    Fields:
    - class: Reference to Class
    - session_number: Sequential session number
    - date: Date of the session
    - start_time: Session start time
    - end_time: Session end time
    - topic: Session topic
    - is_held: Whether session was held
    - created_at: Created timestamp
    """
    
    class_ref = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text=_("Associated class")
    )
    session_number = models.PositiveIntegerField(
        help_text=_("Sequential session number")
    )
    date = models.DateField(
        help_text=_("Date of the session")
    )
    start_time = models.TimeField(
        help_text=_("Session start time")
    )
    end_time = models.TimeField(
        help_text=_("Session end time")
    )
    topic = models.CharField(
        max_length=300,
        help_text=_("Session topic or lecture title")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Additional session notes")
    )
    is_held = models.BooleanField(
        default=True,
        help_text=_("Whether session was actually held")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'start_time']
        verbose_name = _('Session')
        verbose_name_plural = _('Sessions')
        unique_together = [['class_ref', 'date', 'start_time']]
        indexes = [
            models.Index(fields=['class_ref', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.class_ref.code} - Session {self.session_number} ({self.date})"
    
    @property
    def duration_minutes(self):
        """Calculate session duration in minutes."""
        from datetime import datetime, timedelta
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        if end < start:
            end += timedelta(days=1)
        return int((end - start).total_seconds() / 60)


class StudentEnrollment(models.Model):
    """
    StudentEnrollment model for student-class relationships.
    
    Fields:
    - student: Student user
    - class: Enrolled class
    - enrollment_date: Date of enrollment
    - is_active: Whether enrollment is active
    """
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments',
        help_text=_("Student user")
    )
    class_ref = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='students',
        help_text=_("Enrolled class")
    )
    enrollment_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Enrollment date and time")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether enrollment is active")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-enrollment_date']
        verbose_name = _('Student Enrollment')
        verbose_name_plural = _('Student Enrollments')
        unique_together = [['student', 'class_ref']]
        indexes = [
            models.Index(fields=['student', 'class_ref']),
            models.Index(fields=['class_ref', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_ref.code}"
