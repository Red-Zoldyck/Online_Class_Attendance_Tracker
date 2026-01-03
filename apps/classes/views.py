"""
@Red-Zoldyck - Online Class Attendance Tracker
Part of the Online Class Attendance Tracker system

Views for class and session management.

Views:
- ClassViewSet: Class management (CRUD)
- SessionViewSet: Session management
- StudentEnrollmentViewSet: Enrollment management
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, time, timedelta
from apps.classes.models import (
    Class, Session, StudentEnrollment, InstructorApplication,
    Program, YearLevel, Section, Term, Course, SectionCourse, Enrollment
)
from apps.attendance.models import AttendanceRecord, AttendanceIssue
from apps.users.models import User
from apps.classes.serializers import (
    ClassSerializer, ClassDetailSerializer, SessionSerializer,
    StudentEnrollmentSerializer, QuickEnrollRequestSerializer,
    InstructorApplicationSerializer
)
from apps.classes.permissions import IsInstructorOfClass, IsEnrolledInClass, IsInstructorOrAdmin
from apps.users.permissions import IsAdmin
from apps.users.models import Role
from apps.classes.schedule_importer import parse_schedule_csv, import_schedule_data
from apps.classes.services import sync_section_courses_for_term
import logging

logger = logging.getLogger(__name__)


class ClassViewSet(viewsets.ModelViewSet):
    """
    Class management ViewSet.
    
    Instructors and admins can create/edit classes.
    Students and instructors can view classes they have access to.
    """
    
    queryset = Class.objects.select_related('instructor').prefetch_related('sessions')
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'instructor']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['created_at', 'start_date', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'retrieve':
            return ClassDetailSerializer
        return ClassSerializer
    
    def get_queryset(self):
        """Filter classes based on user role."""
        user = self.request.user
        queryset = Class.objects.select_related('instructor').prefetch_related('sessions')
        
        # Admin can see all classes
        if user.role and user.role.name == 'admin':
            return queryset
        
        # Instructor can see their classes
        if user.role and user.role.name == 'instructor':
            return queryset.filter(instructor=user)
        
        # Student can see enrolled classes
        if user.role and user.role.name == 'student':
            return queryset.filter(students__student=user, students__is_active=True)
        
        return queryset.none()
    
    def create(self, request, *args, **kwargs):
        """Create a new class (admin only; instructor can be assigned later)."""
        if not request.user.role or request.user.role.name != 'admin':
            return Response({
                'message': 'Only admins can create subjects/classes.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)

        response = super().create(request, *args, **kwargs)
        if response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED):
            logger.info(f"Class created: {response.data.get('code')} by {request.user.email}")
        return response
    
    def perform_update(self, serializer):
        """Log class updates."""
        serializer.save()
        logger.info(f"Class updated: {serializer.instance.code}")

    def _user_can_manage_class(self, user, class_obj):
        """Check if user is admin or instructor of the class."""
        role = getattr(user, "role", None)
        if role and role.name == 'admin':
            return True
        return class_obj.instructor_id == getattr(user, "id", None)

    def _ensure_student_user(self, payload):
        """Get or create a student user from minimal payload."""
        from apps.users.models import User  # local import to avoid circulars at import time

        email = payload['email'].strip().lower()
        first_name = payload['first_name'].strip()
        last_name = payload['last_name'].strip()
        phone = payload.get('phone_number', '').strip()

        student_role = Role.objects.filter(name=Role.RoleChoices.STUDENT).first()

        try:
            user = User.objects.get(email=email)
            updated = False
            if not user.first_name and first_name:
                user.first_name = first_name
                updated = True
            if not user.last_name and last_name:
                user.last_name = last_name
                updated = True
            if phone and not user.phone_number:
                user.phone_number = phone
                updated = True
            if not user.role and student_role:
                user.role = student_role
                updated = True
            if updated:
                user.save()
            return user
        except User.DoesNotExist:
            pass

        # Build a unique username from email prefix
        base_username = email.split('@', 1)[0][:150] or 'student'
        candidate = base_username
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base_username}-{suffix}"[:150]
            suffix += 1

        user = User(
            email=email,
            username=candidate,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            role=student_role,
            is_active=True,
        )
        user.set_unusable_password()
        user.save()
        return user

    @action(detail=True, methods=['POST'])
    def enroll_student(self, request, pk=None):
        """
        Enroll a student in the class.

        POST /api/v1/classes/{id}/enroll_student/
        """
        class_obj = self.get_object()
        student_id = request.data.get('student_id')

        if not self._user_can_manage_class(request.user, class_obj):
            return Response({
                'message': 'Only the class instructor or admin can enroll students.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)

        if class_obj.available_slots <= 0:
            return Response({
                'message': 'Class capacity reached.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.users.models import User

            if student_id:
                student = User.objects.get(id=student_id)
            else:
                payload_serializer = QuickEnrollRequestSerializer(data=request.data)
                payload_serializer.is_valid(raise_exception=True)
                student = self._ensure_student_user(payload_serializer.validated_data)

            enrollment, created = StudentEnrollment.objects.get_or_create(
                student=student,
                class_ref=class_obj,
                defaults={'is_active': True}
            )

            if not created and not enrollment.is_active:
                enrollment.is_active = True
                enrollment.save()

            logger.info(f"Student {student.email} enrolled in {class_obj.code}")

            return Response({
                'message': 'Student enrolled successfully.',
                'enrollment': StudentEnrollmentSerializer(enrollment).data,
                'status': 'success'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error enrolling student: {str(e)}")
            return Response({
                'message': str(e),
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'])
    def enroll_by_sr_code(self, request, pk=None):
        """Enroll an existing student by SR code (student_number)."""
        class_obj = self.get_object()
        sr_code = (request.data.get('student_number') or '').strip()

        if not self._user_can_manage_class(request.user, class_obj):
            return Response({'message': 'Only the class instructor or admin can enroll students.', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        if not sr_code:
            return Response({'message': 'student_number is required.', 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        if class_obj.available_slots <= 0:
            return Response({'message': 'Class capacity reached.', 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.users.models import User

        try:
            student = User.objects.get(student_number=sr_code)
        except User.DoesNotExist:
            return Response({'message': 'Student not found for given SR code.', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, created = StudentEnrollment.objects.get_or_create(
            student=student,
            class_ref=class_obj,
            defaults={'is_active': True}
        )

        if not created and not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save()

        logger.info(f"Student {student.email} enrolled by SR code in {class_obj.code}")

        return Response({
            'message': 'Student enrolled successfully.',
            'enrollment': StudentEnrollmentSerializer(enrollment).data,
            'status': 'success'
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def apply_instructor(self, request, pk=None):
        """Instructor submits application to teach this class."""
        class_obj = self.get_object()
        user = request.user

        if not user.role or user.role.name != 'instructor':
            return Response({'message': 'Only instructors can apply.', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        if class_obj.instructor_id:
            return Response({'message': 'Class already has an instructor.', 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        app, created = InstructorApplication.objects.get_or_create(
            class_ref=class_obj,
            instructor=user,
            defaults={'status': InstructorApplication.Status.PENDING}
        )

        if not created and app.status == InstructorApplication.Status.PENDING:
            return Response({'message': 'You already have a pending application for this class.', 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        if not created:
            app.status = InstructorApplication.Status.PENDING
            app.note = ''
            app.reviewed_by = None
            app.reviewed_at = None
            app.save()

        return Response({'message': 'Application submitted.', 'application': InstructorApplicationSerializer(app).data, 'status': 'success'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['GET'])
    def applications(self, request, pk=None):
        """List applications for a class (admin only)."""
        if not request.user.role or request.user.role.name != 'admin':
            return Response({'message': 'Admin only.', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        class_obj = self.get_object()
        apps = class_obj.instructor_applications.all()
        return Response(InstructorApplicationSerializer(apps, many=True).data)

    @action(detail=True, methods=['POST'])
    def review_application(self, request, pk=None):
        """Admin approves or rejects an instructor application.

        Payload: {"application_id": int, "decision": "approve"|"reject", "note": "optional"}
        """
        if not request.user.role or request.user.role.name != 'admin':
            return Response({'message': 'Admin only.', 'status': 'error'}, status=status.HTTP_403_FORBIDDEN)

        class_obj = self.get_object()
        app_id = request.data.get('application_id')
        decision = (request.data.get('decision') or '').lower()
        note = request.data.get('note', '')

        try:
            app = class_obj.instructor_applications.get(id=app_id)
        except InstructorApplication.DoesNotExist:
            return Response({'message': 'Application not found for this class.', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        if decision not in ('approve', 'reject'):
            return Response({'message': 'decision must be approve or reject.', 'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        app.note = note
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()

        if decision == 'approve':
            app.status = InstructorApplication.Status.APPROVED
            class_obj.instructor = app.instructor
            class_obj.save(update_fields=['instructor'])
            # Reject other pending applications for this class
            class_obj.instructor_applications.exclude(id=app.id).filter(status=InstructorApplication.Status.PENDING).update(
                status=InstructorApplication.Status.REJECTED,
                reviewed_by=request.user,
                reviewed_at=timezone.now(),
            )
        else:
            app.status = InstructorApplication.Status.REJECTED

        app.save()

        return Response({'message': f'Application {app.status}.', 'application': InstructorApplicationSerializer(app).data, 'status': 'success'})
    
    @action(detail=True, methods=['GET'])
    def students(self, request, pk=None):
        """
        Get list of enrolled students.
        
        GET /api/v1/classes/{id}/students/
        """
        class_obj = self.get_object()
        enrollments = class_obj.students.filter(is_active=True)
        serializer = StudentEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)


class SessionViewSet(viewsets.ModelViewSet):
    """
    Session management ViewSet.
    
    Instructors can create/edit sessions for their classes.
    """
    
    queryset = Session.objects.select_related('class_ref')
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]
    filterset_fields = ['class_ref', 'date', 'is_held']
    ordering_fields = ['date', 'start_time']
    ordering = ['-date']
    
    def get_queryset(self):
        """Filter sessions based on user role."""
        user = self.request.user
        queryset = Session.objects.select_related('class_ref')
        
        # Admin can see all sessions
        if user.role and user.role.name == 'admin':
            return queryset
        
        # Instructor can see sessions for their classes
        if user.role and user.role.name == 'instructor':
            return queryset.filter(class_ref__instructor=user)
        
        # Student can see sessions for enrolled classes
        if user.role and user.role.name == 'student':
            return queryset.filter(
                class_ref__students__student=user,
                class_ref__students__is_active=True
            )
        
        return queryset.none()
    
    def perform_create(self, serializer):
        """Log session creation."""
        serializer.save()
        logger.info(f"Session created: {serializer.instance}")


class StudentEnrollmentViewSet(viewsets.ModelViewSet):
    """
    Student enrollment management ViewSet.
    
    Manage student enrollments in classes.
    """
    
    queryset = StudentEnrollment.objects.select_related('student', 'class_ref')
    serializer_class = StudentEnrollmentSerializer
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]
    filterset_fields = ['class_ref', 'student', 'is_active']
    ordering = ['-enrollment_date']
    
    def get_queryset(self):
        """Filter enrollments based on user role."""
        user = self.request.user
        queryset = StudentEnrollment.objects.select_related('student', 'class_ref')
        
        # Admin can see all enrollments
        if user.role and user.role.name == 'admin':
            return queryset
        
        # Instructor can see enrollments for their classes
        if user.role and user.role.name == 'instructor':
            return queryset.filter(class_ref__instructor=user)
        
        return queryset.none()
    
    @action(detail=True, methods=['POST'])
    def deactivate(self, request, pk=None):
        """
        Deactivate student enrollment.
        
        POST /api/v1/enrollments/{id}/deactivate/
        """
        enrollment = self.get_object()
        enrollment.is_active = False
        enrollment.save()
        logger.info(f"Enrollment deactivated: {enrollment}")
        
        return Response({
            'message': 'Enrollment deactivated.',
            'status': 'success'
        }, status=status.HTTP_200_OK)


# Web Views (Django Templates)

class ClassListView(LoginRequiredMixin, ListView):
    """List classes based on user role."""
    template_name = 'classes/class_list.html'
    context_object_name = 'classes'
    paginate_by = 9
    login_url = 'login'
    
    def get_queryset(self):
        """Get classes based on user role."""
        user = self.request.user
        sort = self.request.GET.get('sort') or 'code'
        order = (self.request.GET.get('order') or 'asc').lower()

        def apply_order(fields):
            if order == 'desc':
                return [f if f.startswith('-') else f"-{f}" for f in fields]
            # asc
            return [f.lstrip('-') for f in fields]

        def build_ordering(sort_key, mapping):
            return apply_order(mapping.get(sort_key, mapping['code']))

        if user.role and user.role.name == 'instructor':
            # Show SectionCourses assigned to this instructor
            sort_map = {
                'code': ['course__code', 'section__code'],
                'section': ['section__code', 'course__code'],
                'term': ['term__school_year', 'term__term', 'course__code'],
                'status': ['is_active', 'course__code'],
                'capacity': ['capacity', 'course__code'],
                'time': ['start_date', 'schedule', 'course__code'],
                'title': ['course__title', 'course__code'],
            }
            ordering = build_ordering(sort, sort_map)
            return SectionCourse.objects.filter(instructor=user, is_active=True).select_related('course', 'section', 'term').order_by(*ordering)
        elif user.role and user.role.name == 'student':
            sort_map = {
                'code': ['course__code', 'section__code'],
                'title': ['course__title', 'course__code'],
                'status': ['is_active', 'course__code'],
                'capacity': ['capacity', 'course__code'],
                'time': ['start_date', 'schedule', 'course__code'],
                'term': ['term__school_year', 'term__term', 'course__code'],
                'section': ['section__code', 'course__code'],
            }
            ordering = build_ordering(sort, sort_map)
            return SectionCourse.objects.filter(
                enrollments__student=user,
                enrollments__is_active=True
            ).select_related('course', 'section', 'term', 'instructor').order_by(*ordering).distinct()
        elif user.role and user.role.name == 'admin':
            sort_map = {
                'code': ['course__code', 'section__code'],
                'title': ['course__title', 'course__code'],
                'status': ['is_active', 'course__code'],
                'capacity': ['capacity', 'course__code'],
                'time': ['start_date', 'schedule', 'course__code'],
                'term': ['term__school_year', 'term__term', 'course__code'],
                'section': ['section__code', 'course__code'],
            }
            ordering = build_ordering(sort, sort_map)
            return SectionCourse.objects.select_related('course', 'section', 'term', 'instructor').order_by(*ordering)
        return Class.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_sort'] = self.request.GET.get('sort', 'code')
        context['current_order'] = (self.request.GET.get('order') or 'asc').lower()
        role = getattr(self.request.user, 'role', None)
        if self.request.user.is_superuser or (role and role.name == 'admin'):
            context['instructors'] = User.objects.filter(role__name='instructor', is_active=True).order_by('first_name', 'last_name')
        return context

    def post(self, request, *args, **kwargs):
        role = getattr(request.user, 'role', None)
        if not (request.user.is_superuser or (role and role.name == 'admin')):
            return redirect('web-users:dashboard')

        action = request.POST.get('action')
        if action == 'assign_instructor':
            section_course_id = request.POST.get('section_course_id')
            instructor_id = request.POST.get('instructor_id') or None
            try:
                section_course = SectionCourse.objects.get(id=section_course_id)
                instructor = User.objects.get(id=instructor_id) if instructor_id else None
                section_course.instructor = instructor
                section_course.save()
                messages.success(request, f"Instructor updated for {section_course.course.code} {section_course.section.code}.")
            except SectionCourse.DoesNotExist:
                messages.error(request, 'Section course not found.')
            except User.DoesNotExist:
                messages.error(request, 'Instructor not found.')
        else:
            messages.error(request, 'Invalid action.')

        query_params = request.GET.urlencode()
        redirect_url = request.path
        if query_params:
            return redirect(f"{redirect_url}?{query_params}")
        return redirect(redirect_url)


class ClassDetailView(LoginRequiredMixin, DetailView):
    """View detailed class information."""
    model = Class
    template_name = 'classes/class_detail.html'
    context_object_name = 'class'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = self.object.sessions.all()
        context['enrollments'] = self.object.students.filter(is_active=True)
        return context


class SectionCourseDetailView(LoginRequiredMixin, DetailView):
    """Detail page for a section-course with enrolled students."""

    model = SectionCourse
    template_name = 'classes/section_course_detail.html'
    context_object_name = 'section_course'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        """Restrict access to admins and assigned instructor."""
        self.object = self.get_object()
        role = getattr(request.user, 'role', None)

        if request.user.is_superuser or (role and role.name == 'admin'):
            return super().dispatch(request, *args, **kwargs)

        if role and role.name == 'instructor' and self.object.instructor_id == request.user.id:
            return super().dispatch(request, *args, **kwargs)

        # Allow students who are enrolled in this section-course to view/report issues
        if role and role.name == 'student':
            is_enrolled = self.object.enrollments.filter(student=request.user, is_active=True).exists()
            if is_enrolled:
                return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'You can only view sections assigned to you.')
        return redirect('web-classes:list')

    def _get_or_create_shadow_class(self):
        """Create a lightweight Class backing this section-course for attendance sessions."""
        code = f"ATT-SC-{self.object.id}"  # keeps Class.code <= 20 and unique
        class_defaults = {
            'name': f"{self.object.course.title} ({self.object.section.code})",
            'description': "Auto-generated for section-course attendance",
            'instructor': self.object.instructor,
            'capacity': self.object.capacity,
            'schedule': self.object.schedule or "Auto attendance",
            'platform_url': self.object.platform_url or '',
            'is_active': self.object.is_active,
            'start_date': timezone.localdate(),
            'end_date': timezone.localdate(),
        }
        class_obj, _ = Class.objects.get_or_create(code=code, defaults=class_defaults)

        # Keep instructor/capacity in sync if it changes later
        updated = False
        if class_obj.instructor_id != getattr(self.object.instructor, 'id', None):
            class_obj.instructor = self.object.instructor
            updated = True
        if class_obj.capacity != self.object.capacity:
            class_obj.capacity = self.object.capacity
            updated = True
        if updated:
            class_obj.save(update_fields=['instructor', 'capacity'])
        return class_obj

    def _get_or_create_today_session(self):
        """Get or create today's attendance session (opens 06:00)."""
        class_obj = self._get_or_create_shadow_class()
        today = timezone.localdate()
        session = Session.objects.filter(class_ref=class_obj, date=today).first()
        if session:
            return session

        session_number = Session.objects.filter(class_ref=class_obj).count() + 1
        return Session.objects.create(
            class_ref=class_obj,
            session_number=session_number,
            date=today,
            start_time=time(6, 0),
            end_time=time(23, 59),
            topic=f"Attendance {self.object.course.code} {today}"
        )

    def _open_time(self, session):
        open_dt = datetime.combine(session.date, time(6, 0))
        return timezone.make_aware(open_dt, timezone.get_current_timezone())

    def _within_schedule_window(self, now):
        """Check if current local time falls within the section-course schedule window.

        Expected schedule format example:
        "TUESDAY/THURSDAY - AFTERNOON | 1:30 - 3:00 PM | B-202"
        Parsing is forgiving; if parsing fails, we allow marking.
        """
        sched = (self.object.schedule or '').strip()
        if not sched:
            return True  # no schedule set, allow

        try:
            parts = [p.strip() for p in sched.split('|')]
            if len(parts) < 2:
                return True  # cannot parse, don't block

            day_part_raw = parts[0]
            time_part = parts[1]

            # Days portion: keep left side before optional '-'
            day_segment = day_part_raw.split('-')[0].strip().upper()
            allowed_days = {d.strip() for d in day_segment.replace(',', '/').split('/') if d.strip()}
            if not allowed_days:
                return True

            local_now = timezone.localtime(now)
            today_name = local_now.strftime('%A').upper()
            if today_name not in allowed_days:
                return False

            # Time range parsing
            time_range = [t.strip() for t in time_part.replace('–', '-').split('-')]
            if len(time_range) != 2:
                return True  # no time window parsed, allow

            def parse_clock(val):
                # Accept formats like "1:30 PM" or "13:30"
                for fmt in ('%I:%M %p', '%I %p', '%H:%M', '%H'):
                    try:
                        return datetime.strptime(val.upper(), fmt).time()
                    except ValueError:
                        continue
                return None

            start_t = parse_clock(time_range[0])
            end_t = parse_clock(time_range[1])
            if not start_t or not end_t:
                return True

            start_dt = timezone.make_aware(datetime.combine(local_now.date(), start_t), timezone.get_current_timezone())
            end_dt = timezone.make_aware(datetime.combine(local_now.date(), end_t), timezone.get_current_timezone())

            return start_dt <= local_now <= end_dt
        except Exception:
            return True  # fail-open to avoid blocking when format is unexpected

    def _lock_deadline(self, session, record=None):
        """Lock is 4 hours after a student's record is marked; fallback to session end."""
        if record and record.marked_at:
            return record.marked_at + timedelta(hours=4)
        end_dt = datetime.combine(session.date, session.end_time)
        return timezone.make_aware(end_dt, timezone.get_current_timezone())

    def _report_deadline(self, session):
        """Reporting window closes 8 hours after lock."""
        lock_deadline = self._lock_deadline(session)
        return lock_deadline + timedelta(hours=8)

    def _can_mark(self, user):
        role = getattr(user, 'role', None)
        if user.is_superuser or (role and role.name == 'admin'):
            return True
        return role and role.name == 'instructor' and self.object.instructor_id == user.id

    def post(self, request, *args, **kwargs):
        """Handle inline attendance marking and student issue reports."""
        self.object = self.get_object()
        action = request.POST.get('action')
        if action == 'report_issue':
            return self._handle_report_issue(request)

        if not self._can_mark(request.user):
            return JsonResponse({'status': 'error', 'message': 'Not allowed'}, status=403)

        student_id = request.POST.get('student_id')
        status_val = request.POST.get('status')
        if not student_id or not status_val:
            return JsonResponse({'status': 'error', 'message': 'student_id and status are required'}, status=400)

        valid_status = dict(AttendanceRecord.AttendanceStatus.choices)
        if status_val not in valid_status:
            return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)

        note_val = (request.POST.get('note') or '').strip()

        session = self._get_or_create_today_session()
        open_time = self._open_time(session)
        now = timezone.now()
        if now < open_time and not (request.user.is_superuser or getattr(request.user, 'role', None) and getattr(request.user.role, 'name', None) == 'admin'):
            return JsonResponse({'status': 'error', 'message': 'Attendance opens at 6:00 AM.'}, status=403)

        # Enforce schedule window for non-admins
        if not (request.user.is_superuser or getattr(request.user, 'role', None) and getattr(request.user.role, 'name', None) == 'admin'):
            if not self._within_schedule_window(now):
                return JsonResponse({'status': 'error', 'message': 'Attendance can only be marked during the scheduled time.'}, status=403)

        role = getattr(request.user, 'role', None)
        is_admin = request.user.is_superuser or (role and role.name == 'admin')
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)

        record = AttendanceRecord.objects.filter(student=student, session=session).first()
        if record and not is_admin:
            lock_deadline = self._lock_deadline(session, record)
            if now > lock_deadline:
                return JsonResponse({'status': 'locked', 'message': 'Attendance is locked for this student. Please contact admin.'}, status=403)

        record, _ = AttendanceRecord.objects.update_or_create(
            student=student,
            session=session,
            defaults={
                'status': status_val,
                'marked_by': request.user,
                'notes': note_val if note_val else '',
            }
        )

        return JsonResponse({
            'status': 'success',
            'record_id': record.id,
            'locked_after': (record.marked_at + timedelta(hours=4)).isoformat() if record.marked_at else None,
            'display': record.get_status_display(),
        })

    def _handle_report_issue(self, request):
        """Allow students to report attendance issues within 8 hours after lock."""
        role = getattr(request.user, 'role', None)
        if not role or role.name != 'student':
            return JsonResponse({'status': 'error', 'message': 'Only students can report issues.'}, status=403)

        session = self._get_or_create_today_session()
        lock_deadline = self._lock_deadline(session)
        report_deadline = self._report_deadline(session)
        now = timezone.now()

        if now < lock_deadline:
            return JsonResponse({'status': 'error', 'message': 'Reporting opens after attendance is locked.'}, status=400)
        if now > report_deadline:
            return JsonResponse({'status': 'error', 'message': 'Reporting window has closed.'}, status=403)

        claimed_status = request.POST.get('claimed_status')
        note = (request.POST.get('note') or '').strip()
        valid_status = dict(AttendanceRecord.AttendanceStatus.choices)
        if claimed_status not in valid_status:
            return JsonResponse({'status': 'error', 'message': 'Invalid claimed status.'}, status=400)

        issue = AttendanceIssue.objects.create(
            student=request.user,
            section_course=self.object,
            session=session,
            claimed_status=claimed_status,
            note=note,
        )

        return JsonResponse({
            'status': 'success',
            'issue_id': issue.id,
            'report_deadline': report_deadline.isoformat(),
            'message': 'Issue submitted. Admin will review and coordinate with the instructor.'
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self._get_or_create_today_session()
        open_time = self._open_time(session)
        now = timezone.now()

        record = AttendanceRecord.objects.filter(student=self.request.user, session=session).first()

        lock_deadline = self._lock_deadline(session, record)
        report_deadline = lock_deadline + timedelta(hours=8)

        attendance_records = AttendanceRecord.objects.filter(session=session)
        attendance_map = {r.student_id: r.status for r in attendance_records}
        attendance_record_map = {r.student_id: r for r in attendance_records}

        enrollments = list(self.object.enrollments.filter(is_active=True).select_related('student'))
        for enrollment in enrollments:
            enrollment.current_status = attendance_map.get(enrollment.student_id)
            rec = attendance_record_map.get(enrollment.student_id)
            enrollment.current_note = rec.notes if rec else ''

        section_members = list(self.object.section.students.select_related('student').filter(is_active=True)) if hasattr(self.object.section, 'students') else []
        for membership in section_members:
            membership.current_status = attendance_map.get(membership.student_id)
            rec = attendance_record_map.get(membership.student_id)
            membership.current_note = rec.notes if rec else ''

        # Per-user lock/report window (students) or default windows for others
        role = getattr(self.request.user, 'role', None)
        if role and role.name == 'student':
            user_record = attendance_record_map.get(self.request.user.id)
            user_lock_deadline = self._lock_deadline(session, user_record)
            user_report_deadline = user_lock_deadline + timedelta(hours=8)
            report_window_open = user_record is not None and now >= user_lock_deadline and now <= user_report_deadline
            lock_deadline = user_lock_deadline
            report_deadline = user_report_deadline
        else:
            report_window_open = now >= lock_deadline and now <= report_deadline

        context['enrollments'] = enrollments
        context['section_members'] = section_members
        context['current_session'] = session
        context['open_time'] = open_time
        context['lock_rule'] = 'Locks 4 hours after a student is marked; opens daily at 06:00.'
        context['lock_deadline'] = lock_deadline
        context['report_deadline'] = report_deadline
        context['report_window_open'] = report_window_open
        context['now'] = now
        context['schedule_rule'] = (self.object.schedule or '').strip()
        return context


class ScheduleAssignmentView(LoginRequiredMixin, TemplateView):
    """Admin page to assign schedules to section courses organized by program, year level, and section."""
    
    template_name = 'classes/schedule_assignment.html'
    login_url = 'web-users:login'

    def dispatch(self, request, *args, **kwargs):
        """Only allow superadmin and admin access."""
        role = getattr(request.user, 'role', None)
        if request.user.is_superuser or (role and role.name == 'admin'):
            return super().dispatch(request, *args, **kwargs)
        return redirect('web-users:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters (support multi-select programs)
        selected_program_ids = self.request.GET.getlist('program')
        selected_year_id = self.request.GET.get('year_level')
        selected_section_id = self.request.GET.get('section')
        selected_term_id = self.request.GET.get('term')
        
        # Base data for filters
        programs_qs = Program.objects.all()
        if selected_program_ids:
            programs_qs = programs_qs.filter(id__in=selected_program_ids)

        context['programs'] = Program.objects.all()
        context['year_levels'] = YearLevel.objects.select_related('program')
        context['sections'] = Section.objects.select_related('program', 'year_level')
        context['terms'] = Term.objects.select_related('program', 'year_level').order_by('-school_year')

        if selected_program_ids:
            context['year_levels'] = context['year_levels'].filter(program_id__in=selected_program_ids)
            context['sections'] = context['sections'].filter(program_id__in=selected_program_ids)
            context['terms'] = context['terms'].filter(program_id__in=selected_program_ids)
        
        # Store selected values
        context['selected_program_ids'] = selected_program_ids
        context['selected_year_id'] = selected_year_id
        context['selected_section_id'] = selected_section_id
        context['selected_term_id'] = selected_term_id
        
        # Get filtered section courses
        section_courses = SectionCourse.objects.select_related(
            'section__program', 'section__year_level',
            'course', 'term', 'instructor'
        ).all()
        
        if selected_program_ids:
            section_courses = section_courses.filter(section__program_id__in=selected_program_ids)
        if selected_year_id:
            section_courses = section_courses.filter(section__year_level_id=selected_year_id)
        if selected_section_id:
            section_courses = section_courses.filter(section_id=selected_section_id)
        if selected_term_id:
            section_courses = section_courses.filter(term_id=selected_term_id)
        
        context['section_courses'] = section_courses.order_by(
            'section__program__code',
            'section__year_level__number',
            'section__code',
            'course__code'
        )
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle schedule updates and CSV import."""
        action = request.POST.get('action')
        
        try:
            if action == 'update_schedule':
                section_course_id = request.POST.get('section_course_id')
                schedule = request.POST.get('schedule', '').strip()
                start_date = request.POST.get('start_date') or None
                end_date = request.POST.get('end_date') or None
                platform_url = request.POST.get('platform_url', '').strip()
                
                section_course = get_object_or_404(SectionCourse, id=section_course_id)
                section_course.schedule = schedule
                section_course.start_date = start_date
                section_course.end_date = end_date
                section_course.platform_url = platform_url
                section_course.save()
                
                messages.success(request, f'Schedule updated for {section_course.course.code} - {section_course.section.code}')
            
            elif action == 'import_csv':
                # Handle CSV file import
                if 'schedule_file' not in request.FILES:
                    messages.error(request, 'No file uploaded.')
                    return redirect('web-classes:schedule-assignment')
                
                csv_file = request.FILES['schedule_file']
                program_id = request.POST.get('import_program_id')
                school_year = request.POST.get('import_school_year', '').strip()
                import_mode = request.POST.get('import_mode', 'all')
                skip_rows_raw = request.POST.get('skip_rows', '')
                
                if not program_id or not school_year:
                    messages.error(request, 'Please select program and school year for import.')
                    return redirect('web-classes:schedule-assignment')
                
                # Get program
                program = get_object_or_404(Program, id=int(program_id))
                
                # Parse CSV
                parsed_data, parse_errors = parse_schedule_csv(csv_file)
                
                if parse_errors:
                    for error in parse_errors:
                        messages.error(request, error)
                
                if not parsed_data:
                    messages.error(request, 'No valid data found in CSV file.')
                    return redirect('web-classes:schedule-assignment')
                
                # Prepare skip rows set
                skip_rows = set()
                if skip_rows_raw:
                    for part in skip_rows_raw.split(','):
                        part = part.strip()
                        if part.isdigit():
                            skip_rows.add(int(part))

                # Import data using per-row term
                import_results = import_schedule_data(parsed_data, program, school_year, mode=import_mode, skip_rows=skip_rows)
                total_imported = import_results['success']
                total_warnings = len(import_results['warnings'])
                total_errors = len(import_results['errors'])
                total_courses_created = import_results.get('courses_created', 0)
                
                # Show results
                if total_errors > 0:
                    messages.error(request, f'❌ {total_errors} error(s) occurred during import.')
                
                if total_warnings > 0:
                    messages.warning(request, f'⚠ {total_warnings} warning(s): Some sections/instructors not found.')
                
                if total_courses_created > 0:
                    messages.info(request, f'📚 {total_courses_created} new course(s) auto-created during import.')
                
                if total_imported > 0:
                    messages.success(request, f'✓ Successfully imported {total_imported} schedule assignment(s)!')
            
            else:
                messages.error(request, 'Unknown action.')
        except Exception as exc:
            messages.error(request, f'Error: {exc}')
        
        # Preserve filter parameters in redirect
        query_params = request.GET.urlencode()
        redirect_url = 'web-classes:schedule-assignment'
        if query_params:
            return redirect(f"{redirect_url}?{query_params}")
        return redirect(redirect_url)
