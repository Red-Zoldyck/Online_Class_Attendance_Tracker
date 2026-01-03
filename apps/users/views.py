"""
Views for user authentication and management.

Views:
- RegisterView: User registration endpoint
- LoginView: User login endpoint
- LogoutView: User logout endpoint
- UserListCreateView: List and create users (admin only)
- UserDetailView: Retrieve, update, delete user
- ChangePasswordView: Change user password
- ProfileView: User profile management
"""

from rest_framework import status, viewsets, generics, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken  # type: ignore
from rest_framework_simplejwt.views import TokenObtainPairView  # type: ignore
from django.contrib.auth import authenticate, login
import csv
import io
import re
from django.urls import reverse
from django.db.models import OuterRef, Subquery, Q, Count
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.contrib.auth import logout
from decimal import Decimal
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from apps.users.models import User, Role, UserProfile
from apps.users.serializers import (
    UserSerializer, UserDetailSerializer, UserRegistrationSerializer,
    ChangePasswordSerializer, RoleSerializer, SelfProfileSerializer
)
from apps.users.permissions import IsAdmin, IsOwnerOrAdmin
from apps.classes.models import (
    Program, YearLevel, Term, Course, ClassSection, SectionCourse, Section,
    SectionCourseApplication, CourseApplication, Session, StudentEnrollment,
    StudentSection, _auto_enroll_for_student_section,
)
from apps.classes.services import sync_sections_for_new_course, sync_section_courses_for_course, sync_section_courses_for_term, sync_all_existing_data, ensure_class_sections_for_term
import logging

logger = logging.getLogger(__name__)


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint.
    
    POST /api/v1/users/register/
    
    Parameters:
    - email (required): User's email address
    - username (required): Unique username
    - first_name (required): User's first name
    - last_name (required): User's last name
    - password (required): User's password (min 8 chars)
    - password_confirm (required): Confirm password
    - phone_number (optional): User's phone number
    - role (required): User's role ID
    """
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Handle user registration."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"New user registered: {user.email}")
        
        return Response({
            'message': 'User registered successfully. Please log in.',
            'user': UserSerializer(user).data,
            'status': 'success'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(views.APIView):
    """
    User login endpoint.
    
    POST /api/v1/users/login/
    
    Parameters:
    - email (required): User's email
    - password (required): User's password
    
    Returns:
    - access_token: JWT access token
    - refresh_token: JWT refresh token
    - user: User information
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle user login."""
        email = request.data.get('email')
        student_number = request.data.get('student_number')
        password = request.data.get('password')

        if not password:
            return Response({
                'message': 'Password is required.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = None
        # Students must use student_number; admins/instructors may use email
        if student_number:
            user = User.objects.filter(student_number=student_number).first()
        elif email:
            candidate = User.objects.filter(email=email).first()
            if candidate and candidate.role and candidate.role.name == Role.RoleChoices.STUDENT:
                return Response({
                    'message': 'Students must log in with student number, not email.',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            user = candidate

        if not user:
            return Response({
                'message': 'Invalid credentials.',
                'status': 'error'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if user.is_account_locked():
            return Response({
                'message': 'Account is temporarily locked. Try again later.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)

        if not user.check_password(password):
            user.increment_login_attempts()
            return Response({
                'message': 'Invalid credentials.',
                'status': 'error'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({
                'message': 'User account is inactive.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)

        user.reset_login_attempts()
        user.last_login_ip = self._get_client_ip(request)
        user.save()

        refresh = RefreshToken.for_user(user)
        logger.info(f"User logged in: {user.email}")

        return Response({
            'message': 'Login successful.',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserSerializer(user).data,
            'status': 'success'
        }, status=status.HTTP_200_OK)


class UserLogoutView(views.APIView):
    """User logout endpoint (stateless; client should discard tokens)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({
            'message': 'Logout successful.',
            'status': 'success'
        }, status=status.HTTP_200_OK)


class SelfProfileView(views.APIView):
    """Allow students/instructors/admin to view/update their own profile, with ID protections."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        serializer = SelfProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Explicitly block student_number or username changes via payload
        blocked_fields = {'student_number', 'username'}
        for f in blocked_fields:
            if f in request.data:
                return Response({
                    'message': f'{f.replace("_", " ").title()} cannot be changed.',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Instructors should not change any instructor ID if stored as username/student_number
        role_name = getattr(getattr(user, 'role', None), 'name', None)
        if role_name == Role.RoleChoices.INSTRUCTOR and ('teacher_id' in request.data or 'instructor_id' in request.data):
            return Response({
                'message': 'Instructor ID cannot be changed.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({
            'message': 'Profile updated successfully.',
            'user': UserDetailSerializer(user).data,
            'status': 'success'
        })


class UserViewSet(viewsets.ModelViewSet):
    """
    User management ViewSet.
    
    Provides CRUD operations for user management.
    Only accessible to admin users.
    """
    
    queryset = User.objects.select_related('role').all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email', 'last_login']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['GET'])
    def me(self, request):
        """
        Get current authenticated user's information.
        
        GET /api/v1/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def change_password(self, request, pk=None):
        """
        Change user password.
        
        POST /api/v1/users/{id}/change_password/
        
        Parameters:
        - old_password (required): Current password
        - new_password (required): New password
        - new_password_confirm (required): Confirm new password
        """
        user = self.get_object()
        
        # Check if user is changing their own password or is admin
        if user != request.user and not request.user.role.name == 'admin':
            return Response({
                'message': 'You can only change your own password.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        logger.info(f"Password changed for user: {user.email}")
        
        return Response({
            'message': 'Password changed successfully.',
            'status': 'success'
        }, status=status.HTTP_200_OK)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Role management ViewSet (Read-only).
    
    Provides READ operations for role information.
    """
    
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']
    ordering = ['name']


# Web Views (Django Templates)

class LoginPageView(TemplateView):
    """Login page that enforces student_number login for students."""

    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('web-users:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        identifier = (request.POST.get('identifier') or '').strip()
        password = request.POST.get('password') or ''

        if not identifier or not password:
            return render(request, self.template_name, {'error': 'Identifier and password are required.'})

        user = None
        try:
            # Prefer student_number for students
            user = User.objects.filter(student_number=identifier).first()
            if not user:
                user = User.objects.filter(email__iexact=identifier).first()
                if user and user.role and user.role.name == Role.RoleChoices.STUDENT:
                    return render(request, self.template_name, {'error': 'Students must log in with their student number, not email.'})
        except Exception:
            user = None

        if not user:
            return render(request, self.template_name, {'error': 'Invalid credentials.'})

        auth_user = authenticate(request, username=user.email, password=password)
        if auth_user is None:
            return render(request, self.template_name, {'error': 'Invalid credentials.'})

        login(request, auth_user)
        return redirect('web-users:dashboard')


class LogoutPageView(DjangoLogoutView):
    """Logout view for web interface."""
    next_page = 'web-users:login'


def logout_redirect(request):
    """Explicit logout handler for GET requests; redirects to login."""
    logout(request)
    return redirect('web-users:login')


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view - accessible to authenticated users."""
    template_name = 'users/dashboard.html'
    login_url = 'web-users:login'
    
    def get_context_data(self, **kwargs):
        """Add context data for dashboard."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        role = getattr(user, 'role', None)

        context['user'] = user

        if role and role.name == 'instructor':
            context['classes_teaching_count'] = SectionCourse.objects.filter(instructor=user, is_active=True).count()
            context['upcoming_sessions_count'] = Session.objects.filter(class_ref__instructor=user, date__gte=timezone.now().date()).count()

        if role and role.name == 'student':
            context['enrolled_classes_count'] = StudentEnrollment.objects.filter(student=user, is_active=True).count()
        return context


class AdminAcademicsView(LoginRequiredMixin, TemplateView):
    """Admin page to manage terms and open subjects."""

    template_name = 'users/admin_academics.html'
    login_url = 'web-users:login'

    def dispatch(self, request, *args, **kwargs):
        role = getattr(request.user, 'role', None)
        if request.user.is_superuser or (role and role.name == 'admin'):
            return super().dispatch(request, *args, **kwargs)
        return redirect('web-users:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programs'] = Program.objects.all()
        context['year_levels'] = YearLevel.objects.select_related('program').all()
        context['terms'] = Term.objects.select_related('program', 'year_level').order_by('-school_year')
        context['courses'] = Course.objects.select_related('program').all()
        context['section_courses'] = SectionCourse.objects.select_related(
            'course', 'term__program', 'term__year_level', 'section'
        ).order_by('-created_at')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        try:
            if action == 'create_term':
                program = get_object_or_404(Program, id=request.POST.get('program'))
                term_choice = request.POST.get('term')
                school_year = request.POST.get('school_year', '').strip()
                
                # Get all year levels for this program
                year_levels = YearLevel.objects.filter(program=program)
                
                created_count = 0
                # Create term for each year level
                for year_level in year_levels:
                    term_obj, created = Term.objects.get_or_create(
                        program=program,
                        year_level=year_level,
                        term=term_choice,
                        school_year=school_year
                    )
                    if created:
                        created_count += 1
                        # Auto-create SectionCourse entries for this term
                        sync_section_courses_for_term(term_obj)
                
                if created_count > 0:
                    messages.success(request, f'Term added successfully for {created_count} year level(s).')
                else:
                    messages.info(request, 'Term already exists for all year levels.')

            elif action == 'create_course':
                program = get_object_or_404(Program, id=request.POST.get('program'))
                code = (request.POST.get('code') or '').strip()
                title = (request.POST.get('title') or '').strip()
                units_raw = request.POST.get('units') or '3'
                suggested_year_level_id = request.POST.get('suggested_year_level')
                suggested_term = request.POST.get('suggested_term')
                description = (request.POST.get('description') or '').strip()

                if not code or not title:
                    messages.error(request, 'Course code and title are required.')
                    return redirect('web-users:admin-academics')

                if not suggested_year_level_id or not suggested_term:
                    messages.error(request, 'Suggested year and term are required for a course.')
                    return redirect('web-users:admin-academics')

                units = Decimal(str(units_raw))
                suggested_year = None

                if suggested_year_level_id:
                    year_level = get_object_or_404(YearLevel, id=suggested_year_level_id)
                    if year_level.program_id != program.id:
                        messages.error(request, 'Suggested year must belong to the same program.')
                        return redirect('web-users:admin-academics')
                    suggested_year = year_level.number

                course = Course.objects.create(
                    program=program,
                    code=code,
                    title=title,
                    units=units,
                    suggested_year=suggested_year,
                    suggested_term=suggested_term,
                    description=description,
                )
                
                # Auto-create SectionCourse entries for this new course
                sc_created, sc_skipped = sync_section_courses_for_course(course)
                created, skipped = sync_sections_for_new_course(course)
                
                msg_parts = ['Course created successfully.']
                if sc_created:
                    msg_parts.append(f'{sc_created} section-course combination(s) created.')
                if created:
                    msg_parts.append(f'{created} class section(s) auto-added.')
                    
                messages.success(request, ' '.join(msg_parts))
            elif action == 'open_subjects_bulk':
                program = get_object_or_404(Program, id=request.POST.get('section_program'))
                term_choice = request.POST.get('section_term')
                school_year = (request.POST.get('section_school_year') or '').strip()

                if not term_choice or not school_year:
                    messages.error(request, 'Term and school year are required.')
                    return redirect('web-users:admin-academics')

                year_levels = YearLevel.objects.filter(program=program)
                created_terms = 0
                created_section_courses = 0
                skipped_section_courses = 0
                created_class_sections = 0
                skipped_class_sections = 0

                for yl in year_levels:
                    term_obj, term_created = Term.objects.get_or_create(
                        program=program,
                        year_level=yl,
                        term=term_choice,
                        school_year=school_year,
                    )
                    if term_created:
                        created_terms += 1

                    sc_created, sc_skipped = sync_section_courses_for_term(term_obj)
                    created_section_courses += sc_created
                    skipped_section_courses += sc_skipped

                    cs_created, cs_skipped = ensure_class_sections_for_term(term_obj)
                    created_class_sections += cs_created
                    skipped_class_sections += cs_skipped

                msg_parts = [
                    f'Term {term_choice} {school_year} processed for {year_levels.count()} year level(s).'
                ]
                if created_terms:
                    msg_parts.append(f'{created_terms} term record(s) created.')
                if created_section_courses:
                    msg_parts.append(f'{created_section_courses} section-course combination(s) opened.')
                if skipped_section_courses:
                    msg_parts.append(f'{skipped_section_courses} existing combination(s) skipped.')
                if created_class_sections:
                    msg_parts.append(f'{created_class_sections} class record(s) added to Class Management.')
                if skipped_class_sections:
                    msg_parts.append(f'{skipped_class_sections} class record(s) already existed.')

                messages.success(request, ' '.join(msg_parts))
            elif action == 'sync_all':
                # Sync all existing courses and terms
                created, skipped = sync_all_existing_data()
                if created:
                    messages.success(request, f'Sync completed! {created} section-course combination(s) created, {skipped} already existed.')
                else:
                    messages.info(request, f'All data already synced. {skipped} existing entries found.')
            else:
                messages.error(request, 'Unknown action.')
        except Exception as exc:
            messages.error(request, f'Error: {exc}')
        return redirect('web-users:admin-academics')


class AdminStudentListView(LoginRequiredMixin, TemplateView):
    """Admin page to view students and their sections."""

    template_name = 'users/admin_students.html'
    login_url = 'web-users:login'

    def dispatch(self, request, *args, **kwargs):
        role = getattr(request.user, 'role', None)
        if request.user.is_superuser or (role and role.name == 'admin'):
            return super().dispatch(request, *args, **kwargs)
        return redirect('web-users:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Latest active section per student (admin-managed) for quick display
        section_subquery = StudentSection.objects.filter(
            student_id=OuterRef('pk'),
            is_active=True,
        ).select_related('section__program', 'section__year_level', 'term').order_by('-created_at')

        students = (
            User.objects.filter(role__name=Role.RoleChoices.STUDENT)
            .select_related('role')
            .annotate(
                active_enrollments=Count('enrollments', filter=Q(enrollments__is_active=True)),
                section_code=Subquery(section_subquery.values('section__code')[:1]),
                section_program=Subquery(section_subquery.values('section__program__code')[:1]),
                section_year=Subquery(section_subquery.values('section__year_level__number')[:1]),
                section_term=Subquery(section_subquery.values('term__term')[:1]),
                section_sy=Subquery(section_subquery.values('term__school_year')[:1]),
                section_id_val=Subquery(section_subquery.values('section_id')[:1]),
                term_id_val=Subquery(section_subquery.values('term_id')[:1]),
            )
        )

        search = (self.request.GET.get('q') or '').strip()
        if search:
            students = students.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(student_number__icontains=search)
            )

        # Filter by section
        filter_section = self.request.GET.get('section')
        if filter_section:
            students = students.filter(section_id_val=filter_section)

        # Filter by term
        filter_term = self.request.GET.get('term')
        if filter_term:
            students = students.filter(term_id_val=filter_term)

        # Sorting
        sort_by = self.request.GET.get('sort', 'last_name')
        if sort_by == 'last_name':
            students = students.order_by('last_name', 'first_name')
        elif sort_by == 'first_name':
            students = students.order_by('first_name', 'last_name')
        elif sort_by == 'email':
            students = students.order_by('email')
        elif sort_by == 'student_number':
            students = students.order_by('student_number')
        elif sort_by == 'section':
            students = students.order_by('section_program', 'section_year', 'section_code', 'last_name')
        elif sort_by == 'enrollments':
            students = students.order_by('-active_enrollments', 'last_name')
        else:
            students = students.order_by('last_name', 'first_name')

        context['students'] = students
        context['search'] = search
        context['filter_section'] = filter_section
        context['filter_term'] = filter_term
        context['sort_by'] = sort_by
        context['sections'] = Section.objects.select_related('program', 'year_level').filter(is_active=True)
        context['terms'] = Term.objects.select_related('program', 'year_level').order_by('-school_year')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'assign_section':
            student_number = (request.POST.get('student_number') or '').strip()
            section_id = request.POST.get('section_id')
            term_id = request.POST.get('term_id')

            if not student_number or not section_id or not term_id:
                messages.error(request, 'Student number, section, and term are required.')
                return redirect('web-users:admin-students')

            student = User.objects.filter(student_number=student_number).first()
            if not student:
                messages.error(request, 'Student not found for that student number.')
                return redirect('web-users:admin-students')

            section = get_object_or_404(Section, id=section_id)
            term = get_object_or_404(Term, id=term_id)

            # Validate that term matches section program/year
            if term.program_id != section.program_id or (term.year_level_id and term.year_level_id != section.year_level_id):
                messages.error(request, 'Selected term does not align with the section program/year level.')
                return redirect('web-users:admin-students')

            StudentSection.objects.update_or_create(
                student=student,
                section=section,
                term=term,
                defaults={'is_active': True},
            )
            messages.success(request, f'Student {student.get_full_name() or student.email} assigned to {section} ({term}).')
            return redirect('web-users:admin-students')

        if action == 'sync_enrollments':
            section_id = request.POST.get('section_id')
            term_id = request.POST.get('term_id')

            qs = StudentSection.objects.filter(is_active=True)
            if section_id:
                qs = qs.filter(section_id=section_id)
            if term_id:
                qs = qs.filter(term_id=term_id)

            synced = 0
            for ss in qs.select_related('section', 'term'):
                _auto_enroll_for_student_section(ss)
                synced += 1

            messages.success(request, f'Enrollment sync finished for {synced} student-section record(s).')
            return redirect('web-users:admin-students')

        if action != 'import_csv':
            messages.error(request, 'Unknown action.')
            return redirect('web-users:admin-students')

        upload = request.FILES.get('file')
        if not upload:
            messages.error(request, 'Please choose a CSV file to import.')
            return redirect('web-users:admin-students')

        try:
            text_file = io.TextIOWrapper(upload.file, encoding='utf-8')
            reader = csv.DictReader(text_file)
        except Exception as exc:  # pragma: no cover - file read errors
            messages.error(request, f'Could not read CSV: {exc}')
            return redirect('web-users:admin-students')

        created = 0
        updated = 0
        skipped = 0
        section_links = 0
        errors = []

        student_role = Role.objects.filter(name=Role.RoleChoices.STUDENT).first()

        def _unique_username(base: str) -> str:
            base_clean = re.sub(r"[^A-Za-z0-9._-]", "", base) or "student"
            base_clean = base_clean[:150]
            candidate = base_clean
            suffix = 1
            while User.objects.filter(username=candidate).exists():
                candidate = f"{base_clean}-{suffix}"[:150]
                suffix += 1
            return candidate

        def _placeholder_email(student_number: str) -> str:
            base = re.sub(r"[^a-zA-Z0-9]+", "", student_number.lower()) or "student"
            candidate = f"{base}@pending.local"[:200]
            suffix = 1
            while User.objects.filter(email=candidate).exists():
                candidate = f"{base}{suffix}@pending.local"[:200]
                suffix += 1
            return candidate

        def _get_case_insensitive(row_dict, keys_list):
            """Get value from dict using case-insensitive key matching."""
            row_lower = {k.lower(): v for k, v in row_dict.items()}
            for key in keys_list:
                if key.lower() in row_lower:
                    return (row_lower[key.lower()] or '').strip()
            return ''

        for row in reader:
            section_code = _get_case_insensitive(row, ['section'])
            student_number = _get_case_insensitive(row, ['student_number', 'student-id', 'student_id', 'sr_code'])
            name_field = _get_case_insensitive(row, ['name', 'names', 'names (last, first)', 'names (last name, first name, middle name)'])
            email = _get_case_insensitive(row, ['email'])
            phone_number = _get_case_insensitive(row, ['phone_number'])
            term_code = _get_case_insensitive(row, ['term'])
            school_year = _get_case_insensitive(row, ['school_year', 'sy'])

            if not section_code or not student_number:
                skipped += 1
                errors.append(f"Missing section/student_number for row: {row}")
                continue

            # Parse name: expect "LAST, FIRST MIDDLE" (from full name column) or "Last, First" or "First Last"
            first_name = ''
            last_name = ''
            if name_field:
                if ',' in name_field:
                    # Format: "LASTNAME, FIRSTNAME MIDDLENAME" or "Last, First"
                    parts = [p.strip() for p in name_field.split(',', 1)]
                    last_name = parts[0]
                    if len(parts) > 1:
                        # Handle "FIRSTNAME MIDDLENAME" or just "FIRSTNAME"
                        first_and_middle = parts[1].split()
                        first_name = first_and_middle[0] if first_and_middle else ''
                else:
                    # Format: "First Last" or "FIRST LAST"
                    parts = name_field.split()
                    if len(parts) >= 2:
                        first_name = ' '.join(parts[:-1])
                        last_name = parts[-1]
                    elif parts:
                        first_name = parts[0]
            # Allow explicit first_name/last_name to override parsed values
            first_name = _get_case_insensitive(row, ['first_name']) or first_name
            last_name = _get_case_insensitive(row, ['last_name']) or last_name

            # Apply title case for proper capitalization
            first_name = first_name.title() if first_name else ''
            last_name = last_name.title() if last_name else ''

            section = Section.objects.select_related('program', 'year_level').filter(code__iexact=section_code).first()
            if not section:
                skipped += 1
                errors.append(f"Section not found: {section_code}")
                continue

            # Choose term: provided or latest matching program/year
            term = None
            term_qs = Term.objects.filter(program=section.program)
            if section.year_level_id:
                term_qs = term_qs.filter(Q(year_level_id=section.year_level_id) | Q(year_level__isnull=True))
            if school_year:
                term_qs = term_qs.filter(school_year=school_year)
            if term_code:
                term_qs = term_qs.filter(term=term_code)
            term = term_qs.order_by('-school_year', '-term').first()
            if not term:
                skipped += 1
                errors.append(f"No term found for section {section_code} (term:{term_code or 'any'} sy:{school_year or 'any'})")
                continue

            # Ensure section-course combos exist for this term
            try:
                sync_section_courses_for_term(term)
            except Exception:
                errors.append(f"Failed to sync section courses for term {term}")

            username_base = student_number
            email_final = email or _placeholder_email(student_number)

            # First check if student_number already exists to avoid unique constraint errors
            user = User.objects.filter(student_number=student_number).first()
            was_created = False
            
            if user:
                # Update existing user
                changed = False
                for field, value in [
                    ('first_name', first_name),
                    ('last_name', last_name),
                    ('phone_number', phone_number),
                    ('email', email_final),
                ]:
                    if value and getattr(user, field) != value:
                        setattr(user, field, value)
                        changed = True
                if username_base and user.username != username_base:
                    new_username = _unique_username(username_base)
                    if user.username != new_username:
                        user.username = new_username
                        changed = True
                if student_role and user.role_id != student_role.id:
                    user.role = student_role
                    changed = True
                if changed:
                    user.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                # Create new user
                defaults = {
                    'username': _unique_username(username_base),
                    'first_name': first_name,
                    'last_name': last_name,
                    'student_number': student_number,
                    'phone_number': phone_number,
                    'role': student_role,
                    'is_active': True,
                }
                user, was_created = User.objects.get_or_create(email=email_final, defaults=defaults)
                if was_created:
                    password_seed = f"{last_name}{student_number[-4:]}" if student_number else last_name or 'changeme'
                    user.set_password(password_seed)
                    user.save(update_fields=['password'])
                    created += 1
                else:
                    # User exists with same email but different student_number - update it
                    user.student_number = student_number
                    user.first_name = first_name or user.first_name
                    user.last_name = last_name or user.last_name
                    user.phone_number = phone_number or user.phone_number
                    if student_role and user.role_id != student_role.id:
                        user.role = student_role
                    user.save()
                    updated += 1

            ss, _ = StudentSection.objects.update_or_create(
                student=user,
                section=section,
                term=term,
                defaults={'is_active': True},
            )
            section_links += 1
            # Auto-enroll into SectionCourse offerings for that section/term
            _auto_enroll_for_student_section(ss)

        messages.success(
            request,
            f'Import finished: {created} created, {updated} updated, {skipped} skipped, {section_links} section links.',
        )
        if errors:
            messages.warning(request, f'Notes: {"; ".join(errors[:5])}' + (' ...' if len(errors) > 5 else ''))
        return redirect('web-users:admin-students')


class InstructorApplicationsAdminView(LoginRequiredMixin, TemplateView):
    """Admin page to review instructor course/section applications."""

    template_name = 'users/admin_instructor_applications.html'
    login_url = 'web-users:login'

    def dispatch(self, request, *args, **kwargs):
        role = getattr(request.user, 'role', None)
        if request.user.is_superuser or (role and role.name == 'admin'):
            return super().dispatch(request, *args, **kwargs)
        return redirect('web-users:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course_applications'] = CourseApplication.objects.select_related('course__program', 'instructor', 'reviewed_by').order_by('-created_at')
        context['section_course_applications'] = SectionCourseApplication.objects.select_related(
            'section_course__course', 'section_course__term__program', 'section_course__term__year_level',
            'instructor', 'reviewed_by'
        ).order_by('-created_at')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action in {"approve_course", "reject_course"}:
            app_id = request.POST.get('course_app_id')
            app = get_object_or_404(CourseApplication, id=app_id)
            if app.status != 'pending':
                messages.warning(request, 'Application already reviewed.')
                return redirect('web-users:admin-instructor-applications')

            if action == 'approve_course':
                app.status = 'approved'
                messages.success(request, 'Course application approved.')
            else:
                app.status = 'rejected'
                messages.success(request, 'Course application rejected.')

            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.save()
            return redirect('web-users:admin-instructor-applications')

        if action in {"approve_section", "reject_section"}:
            app_id = request.POST.get('section_app_id')
            app = get_object_or_404(SectionCourseApplication, id=app_id)
            if app.status != 'pending':
                messages.warning(request, 'Application already reviewed.')
                return redirect('web-users:admin-instructor-applications')

            section_course = app.section_course

            if action == 'approve_section':
                # conflict: another instructor already assigned
                if section_course.instructor and section_course.instructor != app.instructor:
                    messages.error(request, 'Section already has an instructor.')
                    return redirect('web-users:admin-instructor-applications')

                section_course.instructor = app.instructor
                section_course.save()

                app.status = 'approved'
                
                # Auto-create ClassSection for class list
                from apps.classes.models import ClassSection
                ClassSection.objects.get_or_create(
                    course=section_course.course,
                    term=section_course.term,
                    section_code=section_course.section.code,
                    defaults={
                        'schedule': section_course.schedule or '',
                        'capacity': section_course.capacity,
                        'platform_url': section_course.platform_url,
                        'start_date': section_course.start_date,
                        'end_date': section_course.end_date,
                        'is_active': True,
                    }
                )
                
                messages.success(request, 'Section application approved, instructor assigned, and class created.')

                # reject other pending apps for this section_course
                SectionCourseApplication.objects.filter(
                    section_course=section_course,
                    status='pending'
                ).exclude(id=app.id).update(
                    status='rejected',
                    reviewed_by=request.user,
                    reviewed_at=timezone.now()
                )
            else:
                app.status = 'rejected'
                messages.success(request, 'Section application rejected.')

            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.save()
            return redirect('web-users:admin-instructor-applications')

        messages.error(request, 'Unknown action.')
        return redirect('web-users:admin-instructor-applications')


class RegisterPageView(TemplateView):
    """Registration page for web interface."""
    template_name = 'users/register.html'
    
    def get_context_data(self, **kwargs):
        """Add roles to context."""
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.filter(is_active=True)
        return context


class InstructorApplicationView(LoginRequiredMixin, TemplateView):
    """Instructor application view - two-step: apply for course, then select sections."""
    template_name = 'users/instructor_apply.html'
    login_url = 'web-users:login'


class ProfilePageView(LoginRequiredMixin, TemplateView):
    """Self-service profile page (student/instructor/admin) with ID protection."""

    template_name = 'users/profile.html'
    login_url = 'web-users:login'

    def post(self, request, *args, **kwargs):
        user = request.user
        role_name = getattr(getattr(user, 'role', None), 'name', None)

        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('phone_number') or '').strip()
        profile_picture = request.FILES.get('profile_picture')

        # Block ID changes
        if 'student_number' in request.POST or 'username' in request.POST:
            messages.error(request, 'Student number/username cannot be changed.')
            return redirect('web-users:profile')
        if role_name == Role.RoleChoices.INSTRUCTOR and ('teacher_id' in request.POST or 'instructor_id' in request.POST):
            messages.error(request, 'Instructor ID cannot be changed.')
            return redirect('web-users:profile')

        # Unique email check
        if email and User.objects.exclude(id=user.id).filter(email=email).exists():
            messages.error(request, 'Email is already in use.')
            return redirect('web-users:profile')

        changed = False
        for field, value in [
            ('first_name', first_name),
            ('last_name', last_name),
            ('email', email),
            ('phone_number', phone),
        ]:
            if value and getattr(user, field) != value:
                setattr(user, field, value)
                changed = True

        if profile_picture:
            user.profile_picture = profile_picture
            changed = True

        if changed:
            user.save()
            messages.success(request, 'Profile updated.')
        else:
            messages.info(request, 'No changes detected.')

        return redirect('web-users:profile')

    def dispatch(self, request, *args, **kwargs):
        role = getattr(request.user, 'role', None)
        # Only allow instructors or superusers
        if not (request.user.is_superuser or (role and role.name == 'instructor')):
            messages.error(request, 'Only instructors can access this page.')
            return redirect('web-users:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get all course applications by this instructor
        course_applications = CourseApplication.objects.filter(
            instructor=user
        ).select_related('course__program').order_by('-created_at')
        
        # Get courses user can apply for (no existing application)
        applied_course_ids = course_applications.values_list('course_id', flat=True)
        available_courses = Course.objects.exclude(
            id__in=applied_course_ids
        ).select_related('program').order_by('program__code', 'code')
        
        # For approved courses, get available section courses
        approved_courses = course_applications.filter(status='approved')
        sections_by_course = {}
        
        for app in approved_courses:
            # Get section courses for this course
            section_courses = SectionCourse.objects.filter(
                course=app.course,
                is_active=True
            ).select_related(
                'section__program',
                'section__year_level',
                'term__program',
                'term__year_level',
                'instructor'
            ).order_by('term__school_year', 'section__code')
            
            # Get instructor's section applications for this course
            section_applications = SectionCourseApplication.objects.filter(
                instructor=user,
                section_course__course=app.course
            ).select_related('section_course')
            
            app_status_map = {sa.section_course.id: sa for sa in section_applications}
            
            # Build section list with application status
            sections_list = []
            for sc in section_courses:
                sections_list.append({
                    'id': sc.id,
                    'section': sc.section,
                    'term': sc.term,
                    'schedule': sc.schedule,
                    'instructor': sc.instructor,
                    'has_instructor': sc.instructor is not None,
                    'application': app_status_map.get(sc.id),
                })
            
            sections_by_course[app.course.id] = {
                'course': app.course,
                'sections': sections_list
            }
        
        context['available_courses'] = available_courses
        context['course_applications'] = course_applications
        context['sections_by_course'] = sections_by_course
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        user = request.user
        
        try:
            if action == 'apply_course':
                # Step 1: Apply for a course
                course_ids = request.POST.getlist('courses')
                note = request.POST.get('note', '').strip()
                
                if not course_ids:
                    messages.error(request, 'Please select at least one course to apply for.')
                    return redirect('web-users:instructor-apply')
                
                created_count = 0
                for course_id in course_ids:
                    course = get_object_or_404(Course, id=course_id)
                    app, created = CourseApplication.objects.get_or_create(
                        course=course,
                        instructor=user,
                        defaults={'note': note, 'status': 'pending'}
                    )
                    if created:
                        created_count += 1
                    elif app.status == 'rejected':
                        # Allow reapplication
                        app.status = 'pending'
                        app.note = note
                        app.save()
                        created_count += 1
                
                messages.success(request, f'Applied for {created_count} course(s). Wait for admin approval.')
                
            elif action == 'apply_sections':
                # Step 2: Apply for specific sections after course approval
                section_course_ids = request.POST.getlist('section_courses')
                note = request.POST.get('section_note', '').strip()
                
                if not section_course_ids:
                    messages.error(request, 'Please select at least one section.')
                    return redirect('web-users:instructor-apply')
                
                # Check for conflicts
                selected_scs = SectionCourse.objects.filter(id__in=section_course_ids)
                schedules = [sc.schedule for sc in selected_scs if sc.schedule]
                
                for i, sched1 in enumerate(schedules):
                    for sched2 in schedules[i+1:]:
                        if self._schedules_overlap(sched1, sched2):
                            messages.error(request, f'Schedule conflict: "{sched1}" and "{sched2}" overlap.')
                            return redirect('web-users:instructor-apply')
                
                # Check for existing instructor
                conflicts = []
                for sc in selected_scs:
                    if sc.instructor and sc.instructor != user:
                        conflicts.append(f"{sc.course.code} {sc.section.code}")
                
                if conflicts:
                    messages.error(request, 'Already assigned: ' + ', '.join(conflicts))
                    return redirect('web-users:instructor-apply')
                
                # Create section applications
                created_count = 0
                for sc_id in section_course_ids:
                    sc = get_object_or_404(SectionCourse, id=sc_id)
                    app, created = SectionCourseApplication.objects.get_or_create(
                        section_course=sc,
                        instructor=user,
                        defaults={'note': note, 'status': 'pending'}
                    )
                    if created:
                        created_count += 1
                    elif app.status == 'rejected':
                        app.status = 'pending'
                        app.note = note
                        app.save()
                        created_count += 1
                
                messages.success(request, f'Applied for {created_count} section(s). Wait for admin approval.')
                
            elif action == 'withdraw_course':
                application_id = request.POST.get('application_id')
                app = get_object_or_404(CourseApplication, id=application_id, instructor=user)
                
                if app.status == 'approved':
                    messages.error(request, 'Cannot withdraw approved application. Contact admin.')
                else:
                    app.delete()
                    messages.success(request, 'Course application withdrawn.')
            
            elif action == 'withdraw_section':
                application_id = request.POST.get('application_id')
                app = get_object_or_404(SectionCourseApplication, id=application_id, instructor=user)
                
                if app.status == 'approved':
                    messages.error(request, 'Cannot withdraw approved application. Contact admin.')
                else:
                    app.delete()
                    messages.success(request, 'Section application withdrawn.')
            
            else:
                messages.error(request, 'Invalid action.')
                
        except Exception as exc:
            messages.error(request, f'Error: {exc}')
        
        return redirect('web-users:instructor-apply')

    def _schedules_overlap(self, schedule1, schedule2):
        """Check if two schedules overlap."""
        days1 = self._extract_days(schedule1)
        days2 = self._extract_days(schedule2)
        return bool(set(days1) & set(days2))
    
    def _extract_days(self, schedule):
        """Extract day abbreviations from schedule string."""
        day_map = {'Mon': 'Mon', 'Tue': 'Tue', 'Wed': 'Wed', 'Thu': 'Thu', 'Fri': 'Fri', 'Sat': 'Sat', 'Sun': 'Sun'}
        days = []
        for abbr in day_map:
            if abbr in schedule:
                days.append(abbr)
        return days


def page_not_found(request, exception=None):
    """Handle 404 errors."""
    return render(request, 'errors/404.html', status=404)


def server_error(request, exception=None):
    """Handle 500 errors."""
    return render(request, 'errors/500.html', status=500)
