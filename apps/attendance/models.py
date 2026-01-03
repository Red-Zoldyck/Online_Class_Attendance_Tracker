"""
@Red-Zoldyck - Online Class Attendance Tracker
Part of the Online Class Attendance Tracker system

Attendance models for recording and tracking attendance.

Models:
- AttendanceRecord: Individual student attendance record
- AttendanceStatus: Status choices for attendance
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.users.models import User
from apps.classes.models import Session
import logging

logger = logging.getLogger(__name__)


class AttendanceRecord(models.Model):
    """
    AttendanceRecord model for recording student attendance.
    
    Fields:
    - student: Student attending
    - session: Class session
    - status: Attendance status (present, absent, late, excused)
    - check_in_time: Time student checked in
    - check_out_time: Time student checked out
    - notes: Additional attendance notes
    - marked_by: Instructor who marked attendance
    - marked_at: Timestamp of marking
    """
    
    class AttendanceStatus(models.TextChoices):
        """Attendance status choices."""
        PRESENT = 'present', _('Present')
        ABSENT = 'absent', _('Absent')
        LATE = 'late', _('Late')
        EXCUSED = 'excused', _('Excused Absence')
        LEFT_EARLY = 'left_early', _('Left Early')
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text=_("Student who attended")
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text=_("Session attended")
    )
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.ABSENT,
        help_text=_("Attendance status")
    )
    check_in_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Time of check-in")
    )
    check_out_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Time of check-out")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about attendance")
    )
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='marked_attendance_records',
        help_text=_("Instructor who marked attendance")
    )
    marked_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp of marking")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-session__date', 'student__last_name']
        verbose_name = _('Attendance Record')
        verbose_name_plural = _('Attendance Records')
        unique_together = [['student', 'session']]
        indexes = [
            models.Index(fields=['student', 'session']),
            models.Index(fields=['session', 'status']),
            models.Index(fields=['student', 'marked_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.session} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to validate attendance record."""
        if self.check_in_time and self.check_out_time:
            if self.check_in_time > self.check_out_time:
                raise ValueError("Check-in time cannot be after check-out time")
        super().save(*args, **kwargs)
        logger.info(f"Attendance record updated: {self}")
    
    @property
    def duration_minutes(self):
        """Calculate attendance duration in minutes."""
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            return int(duration.total_seconds() / 60)
        return 0
    
    @property
    def is_late(self):
        """Check if student was late."""
        if self.check_in_time and self.session:
            from datetime import datetime, timedelta
            session_start = datetime.combine(self.session.date, self.session.start_time)
            late_threshold = timezone.make_aware(session_start) + timedelta(minutes=15)
            return self.check_in_time > late_threshold
        return False


class AttendanceIssue(models.Model):
    """Student-reported attendance issue for admin review."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        RESOLVED = 'resolved', _('Resolved')

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_issues')
    section_course = models.ForeignKey('classes.SectionCourse', on_delete=models.CASCADE, related_name='attendance_issues')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendance_issues')
    claimed_status = models.CharField(max_length=20, choices=AttendanceRecord.AttendanceStatus.choices)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_attendance_issues')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['section_course', 'created_at']),
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Issue {self.student.get_full_name()} {self.section_course} {self.claimed_status}"
