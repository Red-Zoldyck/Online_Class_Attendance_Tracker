"""
@Red-Zoldyck - Online Class Attendance Tracker
Part of the Online Class Attendance Tracker system

Views for attendance tracking and marking.

Views:
- AttendanceRecordViewSet: CRUD operations for attendance records
- BulkAttendanceView: Bulk attendance marking
"""

from rest_framework import viewsets, status, generics, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Case, When, IntegerField, OuterRef, Subquery
from apps.attendance.models import AttendanceRecord
from apps.attendance.serializers import (
    AttendanceRecordSerializer, AttendanceRecordDetailSerializer,
    BulkAttendanceSerializer
)
from apps.classes.models import Session, StudentEnrollment, StudentSection
from apps.users.permissions import IsAdmin
from apps.classes.permissions import IsInstructorOrAdmin
import logging

logger = logging.getLogger(__name__)


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    """
    Attendance record management ViewSet.
    
    Instructors can mark attendance for their class sessions.
    Students can view their own attendance records.
    """
    
    queryset = AttendanceRecord.objects.select_related(
        'student', 'session', 'marked_by'
    )
    permission_classes = [IsAuthenticated]
    filterset_fields = ['student', 'session', 'status']
    search_fields = ['student__email', 'student__first_name', 'student__last_name']
    ordering_fields = ['marked_at', 'session__date']
    ordering = ['-session__date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'retrieve':
            return AttendanceRecordDetailSerializer
        return AttendanceRecordSerializer
    
    def get_queryset(self):
        """Filter attendance records based on user role."""
        user = self.request.user
        queryset = AttendanceRecord.objects.select_related(
            'student', 'session', 'marked_by'
        )
        
        # Admin can see all records
        if user.role and user.role.name == 'admin':
            return queryset
        
        # Instructor can see records for their classes
        if user.role and user.role.name == 'instructor':
            return queryset.filter(session__class_ref__instructor=user)
        
        # Student can see their own records
        if user.role and user.role.name == 'student':
            return queryset.filter(student=user)
        
        return queryset.none()
    
    def perform_create(self, serializer):
        """Mark the attendance with the current user."""
        serializer.save(marked_by=self.request.user)
        logger.info(f"Attendance marked: {serializer.instance}")
    
    def perform_update(self, serializer):
        """Update attendance record."""
        serializer.save()
        logger.info(f"Attendance updated: {serializer.instance}")
    
    @action(detail=False, methods=['POST'])
    def mark_attendance(self, request):
        """
        Mark attendance for a student in a session.
        
        POST /api/v1/attendance/mark_attendance/
        
        Parameters:
        - student_id (required): Student ID
        - session_id (required): Session ID
        - status (required): Attendance status
        - check_in_time (optional): Check-in time
        - check_out_time (optional): Check-out time
        - notes (optional): Attendance notes
        """
        serializer = AttendanceRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get session and verify instructor permission
            session = Session.objects.get(id=request.data.get('session_id'))
            if (session.class_ref.instructor != request.user and 
                request.user.role.name != 'admin'):
                return Response({
                    'message': 'You can only mark attendance for your classes.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            self.perform_create(serializer)
            return Response({
                'message': 'Attendance marked successfully.',
                'attendance': serializer.data,
                'status': 'success'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error marking attendance: {str(e)}")
            return Response({
                'message': str(e),
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['POST'])
    def bulk_mark(self, request):
        """
        Mark attendance for multiple students.
        
        POST /api/v1/attendance/bulk_mark/
        
        Parameters:
        - session_id (required): Session ID
        - attendances (required): List of attendance records
        """
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            session = Session.objects.get(id=serializer.validated_data['session_id'])
            
            # Verify instructor permission
            if (session.class_ref.instructor != request.user and 
                request.user.role.name != 'admin'):
                return Response({
                    'message': 'You can only mark attendance for your classes.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            created_records = []
            for attendance_data in serializer.validated_data['attendances']:
                from apps.users.models import User
                student = User.objects.get(id=attendance_data['student_id'])
                
                record, created = AttendanceRecord.objects.update_or_create(
                    student=student,
                    session=session,
                    defaults={
                        'status': attendance_data['status'],
                        'notes': attendance_data.get('notes', ''),
                        'marked_by': request.user,
                    }
                )
                created_records.append(record)
            
            logger.info(f"Bulk attendance marked: {len(created_records)} records")
            
            return Response({
                'message': f'Attendance marked for {len(created_records)} students.',
                'count': len(created_records),
                'status': 'success'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error bulk marking attendance: {str(e)}")
            return Response({
                'message': str(e),
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['GET'])
    def session_attendance(self, request):
        """
        Get attendance records for a specific session.
        
        GET /api/v1/attendance/session_attendance/?session_id=1
        """
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response({
                'message': 'session_id parameter is required.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = Session.objects.get(id=session_id)
            records = AttendanceRecord.objects.filter(
                session=session
            ).select_related('student', 'marked_by')
            
            serializer = AttendanceRecordSerializer(records, many=True)
            return Response({
                'session': session.id,
                'records': serializer.data,
                'status': 'success'
            })
        
        except Session.DoesNotExist:
            return Response({
                'message': 'Session not found.',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['GET'])
    def student_attendance(self, request):
        """
        Get attendance records for a specific student across all classes.
        
        GET /api/v1/attendance/student_attendance/?student_id=1
        """
        student_id = request.query_params.get('student_id')
        
        if not student_id:
            student_id = request.user.id
        
        try:
            from apps.users.models import User
            student = User.objects.get(id=student_id)
            
            # Students can only view their own records
            if request.user != student and request.user.role.name != 'admin':
                return Response({
                    'message': 'You can only view your own attendance records.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            records = AttendanceRecord.objects.filter(
                student=student
            ).select_related('session', 'marked_by')
            
            # Calculate statistics
            total_sessions = records.count()
            present_count = records.filter(
                status__in=['present', 'late']
            ).count()
            absent_count = records.filter(
                status__in=['absent']
            ).count()
            excused_count = records.filter(
                status='excused'
            ).count()
            
            attendance_rate = (present_count / total_sessions * 100) if total_sessions > 0 else 0
            
            serializer = AttendanceRecordSerializer(records, many=True)
            
            return Response({
                'student': student.get_full_name(),
                'total_sessions': total_sessions,
                'present': present_count,
                'absent': absent_count,
                'excused': excused_count,
                'attendance_rate': round(attendance_rate, 2),
                'records': serializer.data,
                'status': 'success'
            })
        
        except Exception as e:
            logger.error(f"Error getting student attendance: {str(e)}")
            return Response({
                'message': str(e),
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)


# Web Views (Django Templates)

class SessionAttendanceView(LoginRequiredMixin, DetailView):
    """View for marking attendance for a session."""
    model = Session
    template_name = 'attendance/mark_attendance.html'
    context_object_name = 'session'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get enrolled students for this class
        session = self.get_object()
        section_subquery = StudentSection.objects.filter(
            student_id=OuterRef('student_id'),
            is_active=True
        ).select_related('section__program', 'section__year_level').order_by('-created_at')

        context['students'] = StudentEnrollment.objects.filter(
            class_ref=session.class_ref,
            is_active=True
        ).select_related('student').annotate(
            section_code=Subquery(section_subquery.values('section__code')[:1]),
            section_program=Subquery(section_subquery.values('section__program__code')[:1]),
            section_year=Subquery(section_subquery.values('section__year_level__number')[:1]),
        )
        
        # Get existing attendance records for this session
        context['attendance_records'] = AttendanceRecord.objects.filter(
            session=session
        ).select_related('student', 'marked_by').annotate(
            section_code=Subquery(section_subquery.values('section__code')[:1]),
            section_program=Subquery(section_subquery.values('section__program__code')[:1]),
            section_year=Subquery(section_subquery.values('section__year_level__number')[:1]),
        )
        
        return context


class StudentAttendanceView(LoginRequiredMixin, ListView):
    """View for viewing student attendance records."""
    model = AttendanceRecord
    template_name = 'attendance/student_attendance.html'
    context_object_name = 'records'
    paginate_by = 20
    login_url = 'login'
    
    def get_queryset(self):
        """Get attendance records for current user."""
        return AttendanceRecord.objects.filter(
            student=self.request.user
        ).select_related('session')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        records = self.get_queryset()
        
        # Calculate statistics
        context['total_sessions'] = records.count()
        context['present_count'] = records.filter(
            status__in=['present', 'late']
        ).count()
        context['absent_count'] = records.filter(
            status='absent'
        ).count()
        context['excused_count'] = records.filter(
            status='excused'
        ).count()
        
        if context['total_sessions'] > 0:
            context['attendance_rate'] = round(
                (context['present_count'] / context['total_sessions']) * 100, 2
            )
        else:
            context['attendance_rate'] = 0
        
        return context
