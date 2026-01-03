"""
Admin configuration for Class models.
"""

from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from django.shortcuts import redirect
from apps.classes.models import (
    Class,
    Session,
    StudentEnrollment,
    Program,
    YearLevel,
    Term,
    Course,
    Section,
    SectionCourse,
    StudentSection,
    Enrollment,
    ClassSection,
    TeachingAssignment,
    InstructorApplication,
    SectionCourseApplication,
    CourseApplication,
)
from apps.classes.services import sync_sections_for_new_course


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """Admin interface for Class model."""
    
    list_display = [
        'code', 'name', 'get_instructor_name', 'enrolled_count',
        'capacity', 'is_active_display', 'start_date'
    ]
    list_filter = ['is_active', 'instructor', 'start_date', 'created_at']
    search_fields = ['code', 'name', 'description', 'instructor__email']
    readonly_fields = ['created_at', 'updated_at', 'enrolled_count', 'available_slots']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Class Information', {
            'fields': ('code', 'name', 'description', 'instructor')
        }),
        ('Schedule & Capacity', {
            'fields': ('start_date', 'end_date', 'schedule', 'capacity', 'enrolled_count', 'available_slots')
        }),
        ('Platform', {
            'fields': ('platform_url',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_instructor_name(self, obj):
        """Display instructor name."""
        return obj.instructor.get_full_name()
    get_instructor_name.short_description = 'Instructor'
    
    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Status'


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin interface for Session model."""
    
    list_display = [
        'get_class_code', 'session_number', 'date', 'start_time',
        'end_time', 'topic', 'is_held_display'
    ]
    list_filter = ['is_held', 'class_ref', 'date', 'created_at']
    search_fields = ['class_ref__code', 'topic', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date', '-start_time']
    
    fieldsets = (
        ('Class & Session', {
            'fields': ('class_ref', 'session_number')
        }),
        ('Schedule', {
            'fields': ('date', 'start_time', 'end_time')
        }),
        ('Content', {
            'fields': ('topic', 'notes')
        }),
        ('Status', {
            'fields': ('is_held',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_class_code(self, obj):
        """Display class code."""
        return obj.class_ref.code
    get_class_code.short_description = 'Class Code'
    
    def is_held_display(self, obj):
        """Display session held status."""
        if obj.is_held:
            return format_html('<span style="color: green;">✓ Held</span>')
        return format_html('<span style="color: red;">✗ Not Held</span>')
    is_held_display.short_description = 'Session Held'


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    """Admin interface for StudentEnrollment model."""
    
    list_display = [
        'get_student_name', 'get_class_code', 'enrollment_date',
        'is_active_display', 'created_at'
    ]
    list_filter = ['class_ref', 'is_active', 'enrollment_date', 'created_at']
    search_fields = ['student__email', 'student__first_name', 'student__last_name', 'class_ref__code']
    readonly_fields = ['enrollment_date', 'created_at', 'updated_at']
    ordering = ['-enrollment_date']
    
    fieldsets = (
        ('Enrollment Information', {
            'fields': ('student', 'class_ref', 'enrollment_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Display student name."""
        return obj.student.get_full_name()
    get_student_name.short_description = 'Student'
    
    def get_class_code(self, obj):
        """Display class code."""
        return obj.class_ref.code
    get_class_code.short_description = 'Class'
    
    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Status'


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    fields = ['code', 'name']


@admin.register(YearLevel)
class YearLevelAdmin(admin.ModelAdmin):
    list_display = ['program', 'number']
    list_filter = ['program']
    search_fields = ['program__code']


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ['program', 'year_level', 'term', 'school_year']
    list_filter = ['program', 'year_level__number', 'term', 'school_year']
    search_fields = ['program__code', 'school_year']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['program', 'year_level', 'code', 'capacity', 'is_active']
    list_filter = ['program', 'year_level__number', 'is_active']
    search_fields = ['program__code', 'code']


@admin.register(SectionCourse)
class SectionCourseAdmin(admin.ModelAdmin):
    list_display = ['section', 'course', 'term', 'capacity', 'is_active']
    list_filter = ['section__program', 'term__school_year', 'is_active']
    search_fields = ['section__code', 'course__code', 'term__school_year']


@admin.register(StudentSection)
class StudentSectionAdmin(admin.ModelAdmin):
    list_display = ['student', 'section', 'term', 'is_active']
    list_filter = ['section__program', 'term__school_year', 'is_active']
    search_fields = ['student__email', 'section__code', 'term__school_year']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'section', 'term', 'is_active']
    list_filter = ['term__school_year', 'section__program', 'is_active']
    search_fields = ['student__email', 'course__code', 'section__code']


class CourseAdminForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['program', 'code', 'title', 'units', 'suggested_year', 'suggested_term', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['suggested_year'].required = True
        self.fields['suggested_term'].required = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ['program', 'code', 'title', 'units', 'suggested_year', 'suggested_term']
    list_filter = ['program', 'suggested_year', 'suggested_term']
    search_fields = ['code', 'title', 'program__code']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        created, skipped = sync_sections_for_new_course(obj)
        if created:
            self.message_user(
                request,
                f"Auto-created {created} section(s) matching existing codes for this term.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} existing section(s) with the same code.",
                level=messages.WARNING,
            )


class ClassSectionChangeForm(forms.ModelForm):
    program = forms.ModelChoiceField(queryset=Program.objects.all(), label='Program')

    class Meta:
        model = ClassSection
        fields = ['program', 'course', 'term', 'section_code', 'capacity', 'schedule', 'is_active', 'platform_url', 'start_date', 'end_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        program = None

        if self.is_bound:
            program_id = self.data.get('program')
            if program_id:
                program = Program.objects.filter(id=program_id).first()
        elif self.instance and self.instance.pk:
            program = self.instance.term.program

        if program:
            self.fields['course'].queryset = Course.objects.filter(program=program)
            self.fields['term'].queryset = Term.objects.filter(program=program)
            self.fields['program'].initial = program

        self.fields['section_code'].help_text = 'e.g., A'

    def clean(self):
        cleaned = super().clean()
        program = cleaned.get('program')
        course = cleaned.get('course')
        term = cleaned.get('term')

        if program and course and course.program_id != program.id:
            self.add_error('course', 'Course must belong to the selected program.')
        if program and term and term.program_id != program.id:
            self.add_error('term', 'Term must belong to the selected program.')

        return cleaned


class ClassSectionAddForm(forms.ModelForm):
    program = forms.ModelChoiceField(queryset=Program.objects.all(), label='Program')

    class Meta:
        model = ClassSection
        fields = ['program', 'term', 'section_code', 'capacity', 'schedule', 'is_active', 'platform_url', 'start_date', 'end_date', 'course']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matching_courses = []

        # Hide course field; we'll populate it automatically
        self.fields['course'].required = False
        self.fields['course'].widget = forms.HiddenInput()
        self.fields['course'].queryset = Course.objects.none()

        program = None
        if self.is_bound:
            program_id = self.data.get('program')
            if program_id:
                program = Program.objects.filter(id=program_id).first()
        elif self.initial.get('term'):
            term = Term.objects.filter(id=self.initial.get('term')).select_related('program').first()
            program = term.program if term else None

        if program:
            self.fields['term'].queryset = Term.objects.filter(program=program).select_related('year_level')

        self.fields['section_code'].help_text = 'e.g., A'

    def clean(self):
        cleaned = super().clean()
        program = cleaned.get('program')
        term = cleaned.get('term')

        if not program or not term:
            return cleaned

        if term.program_id != program.id:
            self.add_error('term', 'Term must belong to the selected program.')
            return cleaned

        # Find courses that match the term's year and term
        self.matching_courses = list(
            Course.objects.filter(
                program=program,
                suggested_year=term.year_level.number,
                suggested_term=term.term,
            )
        )

        if not self.matching_courses:
            self.add_error(None, 'No courses found for this program, year level, and term. Ensure courses have suggested year/term set.')
            return cleaned

        # Set a placeholder course so model validation passes; actual save will create per-course
        cleaned['course'] = self.matching_courses[0]
        return cleaned


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    form = ClassSectionChangeForm
    list_display = ['course', 'section_code', 'term', 'capacity', 'is_active']
    list_filter = ['term__program', 'term__year_level', 'term__term', 'is_active']
    search_fields = ['course__code', 'section_code', 'term__school_year']
    fields = ['program', 'course', 'term', 'section_code', 'capacity', 'schedule', 'is_active', 'platform_url', 'start_date', 'end_date']

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = ClassSectionAddForm
        else:
            kwargs['form'] = self.form
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)

        # Add: create sections for all matching courses
        section_code = form.cleaned_data['section_code']
        capacity = form.cleaned_data['capacity']
        schedule = form.cleaned_data['schedule']
        is_active = form.cleaned_data['is_active']
        platform_url = form.cleaned_data['platform_url']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        term = form.cleaned_data['term']

        created = 0
        skipped = 0
        for course in getattr(form, 'matching_courses', []):
            section, was_created = ClassSection.objects.get_or_create(
                course=course,
                term=term,
                section_code=section_code,
                defaults={
                    'capacity': capacity,
                    'schedule': schedule,
                    'is_active': is_active,
                    'platform_url': platform_url,
                    'start_date': start_date,
                    'end_date': end_date,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        if created:
            self.message_user(
                request,
                f"Created {created} section(s) for program {term.program.code}, Y{term.year_level.number}, T{term.term}.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} existing section(s) with the same code.",
                level=messages.WARNING,
            )

    def response_add(self, request, obj, post_url_continue=None):
        # After custom creation, go back to changelist
        return redirect('..')


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['section', 'instructor', 'assigned_at']
    list_filter = ['section__term__program']
    search_fields = ['section__course__code', 'instructor__email']


@admin.register(InstructorApplication)
class InstructorApplicationAdmin(admin.ModelAdmin):
    list_display = ['class_ref', 'instructor', 'status', 'reviewed_by', 'reviewed_at', 'created_at']
    list_filter = ['status', 'class_ref__code']
    search_fields = ['class_ref__code', 'instructor__email']


@admin.register(SectionCourseApplication)
class SectionCourseApplicationAdmin(admin.ModelAdmin):
    """Admin for instructor section course applications."""
    list_display = ['section_course', 'instructor', 'status', 'reviewed_by', 'reviewed_at', 'created_at']
    list_filter = ['status', 'section_course__course__code', 'section_course__term__school_year']
    search_fields = ['section_course__course__code', 'instructor__email', 'instructor__first_name', 'instructor__last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Application Details', {
            'fields': ('section_course', 'instructor', 'status', 'note')
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        """Approve selected applications and assign instructors."""
        from django.utils import timezone
        approved_count = 0
        conflict_count = 0
        
        for app in queryset.filter(status='pending'):
            sc = app.section_course
            # Check if already has instructor
            if sc.instructor and sc.instructor != app.instructor:
                conflict_count += 1
                continue
            
            # Assign instructor
            sc.instructor = app.instructor
            sc.save()
            
            # Update application
            app.status = 'approved'
            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.save()
            
            # Reject other pending applications for this section course
            SectionCourseApplication.objects.filter(
                section_course=sc,
                status='pending'
            ).exclude(id=app.id).update(
                status='rejected',
                reviewed_by=request.user,
                reviewed_at=timezone.now()
            )
            
            approved_count += 1
        
        if approved_count:
            self.message_user(request, f"{approved_count} application(s) approved and instructor(s) assigned.")
        if conflict_count:
            self.message_user(request, f"{conflict_count} application(s) skipped due to existing instructor assignment.", level=messages.WARNING)
    
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        """Reject selected applications."""
        from django.utils import timezone
        count = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f"{count} application(s) rejected.")
    
    reject_applications.short_description = "Reject selected applications"


@admin.register(CourseApplication)
class CourseApplicationAdmin(admin.ModelAdmin):
    """Admin for instructor course applications (first step)."""
    list_display = ['course', 'instructor', 'status', 'reviewed_by', 'reviewed_at', 'created_at']
    list_filter = ['status', 'course__program', 'course__code']
    search_fields = ['course__code', 'course__title', 'instructor__email', 'instructor__first_name', 'instructor__last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Application Details', {
            'fields': ('course', 'instructor', 'status', 'note')
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        """Approve selected course applications."""
        from django.utils import timezone
        count = queryset.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f"{count} course application(s) approved. Instructors can now select sections.")
    
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        """Reject selected course applications."""
        from django.utils import timezone
        count = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f"{count} application(s) rejected.")
    
    reject_applications.short_description = "Reject selected applications"
