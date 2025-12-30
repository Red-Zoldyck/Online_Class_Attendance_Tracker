"""
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
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.classes.models import Class, Session, StudentEnrollment
from apps.classes.serializers import (
    ClassSerializer, ClassDetailSerializer, SessionSerializer,
    StudentEnrollmentSerializer
)
from apps.classes.permissions import IsInstructorOfClass, IsEnrolledInClass, IsInstructorOrAdmin
from apps.users.permissions import IsAdmin
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
        """Create a new class (instructor only)."""
        if not request.user.role or request.user.role.name not in ['instructor', 'admin']:
            return Response({
                'message': 'Only instructors can create classes.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Set instructor to current user on creation."""
        serializer.save(instructor=self.request.user)
        logger.info(f"Class created: {serializer.instance.code} by {self.request.user.email}")
    
    def perform_update(self, serializer):
        """Log class updates."""
        serializer.save()
        logger.info(f"Class updated: {serializer.instance.code}")
    
    @action(detail=True, methods=['POST'])
    def enroll_student(self, request, pk=None):
        """
        Enroll a student in the class.
        
        POST /api/v1/classes/{id}/enroll_student/
        
        Parameters:
        - student_id (required): ID of student to enroll
        """
        class_obj = self.get_object()
        student_id = request.data.get('student_id')
        
        if not student_id:
            return Response({
                'message': 'student_id is required.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check permission (instructor of class or admin)
        if class_obj.instructor != request.user and request.user.role.name != 'admin':
            return Response({
                'message': 'Only the class instructor can enroll students.',
                'status': 'error'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from apps.users.models import User
            student = User.objects.get(id=student_id)
            
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
    paginate_by = 10
    login_url = 'login'
    
    def get_queryset(self):
        """Get classes based on user role."""
        user = self.request.user
        if user.role and user.role.name == 'instructor':
            return Class.objects.filter(instructor=user)
        elif user.role and user.role.name == 'student':
            return Class.objects.filter(students__student=user, students__is_active=True)
        elif user.role and user.role.name == 'admin':
            return Class.objects.all()
        return Class.objects.none()


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
