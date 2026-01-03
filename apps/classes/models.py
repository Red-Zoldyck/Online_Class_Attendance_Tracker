"""
@Red-Zoldyck - Online Class Attendance Tracker
Part of the Online Class Attendance Tracker system

Class and Session models for the Attendance Tracker.

Models:
- Class: Online class information
- Session: Individual class session
- StudentEnrollment: Student enrollment in a class
"""

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='taught_classes',
        help_text=_("Instructor for this class (can be unassigned until approved)")
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


class Program(models.Model):
    """Top-level program (e.g., BSCS, BSIT)."""

    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Section(models.Model):
    """Stable section aligned to a program and year level (not tied to term)."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="sections")
    year_level = models.ForeignKey("YearLevel", on_delete=models.CASCADE, related_name="sections")
    code = models.CharField(max_length=20, help_text=_("Section code, e.g., A"))
    capacity = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("program", "year_level", "code")]
        ordering = ["program__code", "year_level__number", "code"]

    def __str__(self):
        return f"{self.program.code} Y{self.year_level.number} {self.code}"


class YearLevel(models.Model):
    """Year level within a program (1-4)."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="year_levels")
    number = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = [("program", "number")]
        ordering = ["program__code", "number"]

    def __str__(self):
        return f"{self.program.code} Y{self.number}"


class Term(models.Model):
    """Semester/term within a program (applies to all year levels)."""

    class TermChoice(models.TextChoices):
        FIRST = "1", _("1st Sem")
        SECOND = "2", _("2nd Sem")

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="terms")
    year_level = models.ForeignKey(YearLevel, on_delete=models.CASCADE, related_name="terms", null=True, blank=True, help_text=_("Optional: leave blank to apply to all year levels"))
    term = models.CharField(max_length=1, choices=TermChoice.choices)
    school_year = models.CharField(max_length=9, help_text=_("Format: 2025-2026"))

    class Meta:
        # Allow multiple entries per program if year_level is None (applies to all)
        unique_together = [("program", "year_level", "term", "school_year")]
        ordering = ["program__code", "school_year", "year_level__number", "term"]

    def __str__(self):
        # year_level can be null; handle gracefully
        yl = self.year_level.number if self.year_level else "all"
        return f"{self.program.code} Y{yl} T{self.term} {self.school_year}"


class SectionCourse(models.Model):
    """Assignment of a course to a section for a specific term."""

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="section_courses")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="section_courses")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="section_courses")
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_section_courses", help_text=_("Assigned instructor"))
    schedule = models.CharField(max_length=200, blank=True, help_text=_("Schedule for this section offering"))
    platform_url = models.URLField(blank=True)
    capacity = models.PositiveIntegerField(default=40)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("section", "course", "term")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.section} -> {self.course.code} ({self.term})"


class Course(models.Model):
    """Catalog course/subject belonging to a program."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="courses")
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    units = models.DecimalField(max_digits=4, decimal_places=1, default=3)
    suggested_year = models.PositiveSmallIntegerField(null=True, blank=True)
    suggested_term = models.CharField(
        max_length=1, choices=Term.TermChoice.choices, null=True, blank=True
    )
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("program", "code")]
        ordering = ["program__code", "code"]

    def __str__(self):
        return f"{self.code} - {self.title}"


class ClassSection(models.Model):
    """Concrete offering of a course in a specific term (section)."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="sections")
    section_code = models.CharField(max_length=20, help_text=_("e.g., CS101-A"))
    capacity = models.PositiveIntegerField(default=40)
    schedule = models.CharField(max_length=200, help_text=_("e.g., Mon/Wed 10:00-11:30"))
    platform_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("course", "term", "section_code")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course.code} {self.section_code} ({self.term})"

    @property
    def enrolled_count(self):
        return self.enrollments.filter(is_active=True).count()

    @property
    def available_slots(self):
        return max(0, self.capacity - self.enrolled_count)


class StudentSection(models.Model):
    """Student assignment to a section for a given term."""

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="section_memberships")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="students")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="student_sections")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("student", "section", "term")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.get_full_name()} -> {self.section} ({self.term})"


class Enrollment(models.Model):
    """Derived enrollment of a student into a course for a section and term."""

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments_v2")
    section_course = models.ForeignKey(SectionCourse, on_delete=models.CASCADE, related_name="enrollments")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="enrollments")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="enrollments")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("student", "course", "term")]
        indexes = [
            models.Index(fields=["student", "term"]),
            models.Index(fields=["section", "term"]),
        ]

    def __str__(self):
        return f"{self.student.get_full_name()} -> {self.course.code} ({self.term})"


class TeachingAssignment(models.Model):
    """Instructor assignment to a class section."""

    section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="teaching_assignments")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="teaching_sections")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("section", "instructor")]
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.section} -> {self.instructor.get_full_name()}"


class InstructorApplication(models.Model):
    """Instructor applies to teach a class; admin reviews."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="instructor_applications")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="class_applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_applications")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("class_ref", "instructor")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.instructor.get_full_name()} -> {self.class_ref.code} ({self.status})"


class SectionCourseApplication(models.Model):
    """Instructor application to teach specific section courses."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    section_course = models.ForeignKey(SectionCourse, on_delete=models.CASCADE, related_name="applications")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="section_course_applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True, help_text=_("Application note or message"))
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_section_applications")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("section_course", "instructor")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["instructor", "status"]),
            models.Index(fields=["section_course", "status"]),
        ]

    def __str__(self):
        return f"{self.instructor.get_full_name()} -> {self.section_course} ({self.status})"


class CourseApplication(models.Model):
    """Instructor application to teach a course (first step before section selection)."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="instructor_applications")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="course_applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True, help_text=_("Application note or message"))
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_course_applications")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("course", "instructor")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["instructor", "status"]),
            models.Index(fields=["course", "status"]),
        ]

    def __str__(self):
        return f"{self.instructor.get_full_name()} -> {self.course.code} ({self.status})"


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


def _auto_enroll_for_section_course(section_course: SectionCourse):
    students = StudentSection.objects.filter(
        section=section_course.section,
        term=section_course.term,
        is_active=True,
    ).select_related("student")
    for ss in students:
        try:
            Enrollment.objects.get_or_create(
                student=ss.student,
                course=section_course.course,
                term=section_course.term,
                defaults={
                    "section_course": section_course,
                    "section": section_course.section,
                    "is_active": True,
                },
            )
        except Exception:
            # Skip if enrollment already exists (handles race conditions)
            pass


def _auto_enroll_for_student_section(student_section: StudentSection):
    section_courses = SectionCourse.objects.filter(
        section=student_section.section,
        term=student_section.term,
        is_active=True,
    ).select_related("course")
    for sc in section_courses:
        try:
            Enrollment.objects.get_or_create(
                student=student_section.student,
                course=sc.course,
                term=sc.term,
                defaults={
                    "section_course": sc,
                    "section": sc.section,
                    "is_active": True,
                },
            )
        except Exception:
            # Skip if enrollment already exists (handles race conditions)
            pass


@receiver(post_save, sender=SectionCourse)
def create_enrollments_on_section_course(sender, instance, created, **kwargs):
    if created:
        _auto_enroll_for_section_course(instance)


@receiver(post_save, sender=StudentSection)
def create_enrollments_on_student_section(sender, instance, created, **kwargs):
    if created:
        _auto_enroll_for_student_section(instance)
