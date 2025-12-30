"""
Service layer for generating attendance reports.

Services:
- AttendanceReportService: Generate various attendance reports
- ClassReportService: Generate class-level reports
- StudentReportService: Generate student-level reports
"""

from django.db.models import Count, Q, F, Case, When, IntegerField
from django.utils import timezone
from datetime import datetime, timedelta
from apps.attendance.models import AttendanceRecord
from apps.classes.models import Class, Session, StudentEnrollment
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)


class AttendanceReportService:
    """Service for generating attendance reports."""
    
    @staticmethod
    def get_class_attendance_summary(class_id, start_date=None, end_date=None):
        """
        Get attendance summary for a class.
        
        Args:
            class_id: ID of the class
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            Dictionary with attendance statistics
        """
        try:
            class_obj = Class.objects.get(id=class_id)
            
            # Base queryset
            records = AttendanceRecord.objects.filter(
                session__class_ref=class_obj
            )
            
            # Apply date filters
            if start_date:
                records = records.filter(session__date__gte=start_date)
            if end_date:
                records = records.filter(session__date__lte=end_date)
            
            # Calculate statistics
            total_records = records.count()
            present = records.filter(status__in=['present', 'late']).count()
            absent = records.filter(status='absent').count()
            excused = records.filter(status='excused').count()
            left_early = records.filter(status='left_early').count()
            
            attendance_rate = (present / total_records * 100) if total_records > 0 else 0
            
            logger.info(f"Generated attendance summary for class {class_id}")
            
            return {
                'class': {
                    'id': class_obj.id,
                    'code': class_obj.code,
                    'name': class_obj.name,
                },
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                },
                'statistics': {
                    'total_records': total_records,
                    'present': present,
                    'absent': absent,
                    'excused': excused,
                    'left_early': left_early,
                    'attendance_rate': round(attendance_rate, 2),
                }
            }
        except Class.DoesNotExist:
            logger.error(f"Class {class_id} not found")
            raise
    
    @staticmethod
    def get_student_attendance_summary(student_id, class_id=None, start_date=None, end_date=None):
        """
        Get attendance summary for a student.
        
        Args:
            student_id: ID of the student
            class_id: Optional filter to specific class
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            Dictionary with student attendance statistics
        """
        try:
            student = User.objects.get(id=student_id)
            
            # Base queryset
            records = AttendanceRecord.objects.filter(student=student)
            
            # Apply filters
            if class_id:
                records = records.filter(session__class_ref_id=class_id)
            if start_date:
                records = records.filter(session__date__gte=start_date)
            if end_date:
                records = records.filter(session__date__lte=end_date)
            
            # Calculate statistics
            total = records.count()
            present = records.filter(status__in=['present', 'late']).count()
            absent = records.filter(status='absent').count()
            excused = records.filter(status='excused').count()
            late = records.filter(status='late').count()
            left_early = records.filter(status='left_early').count()
            
            attendance_rate = (present / total * 100) if total > 0 else 0
            
            logger.info(f"Generated attendance summary for student {student_id}")
            
            return {
                'student': {
                    'id': student.id,
                    'name': student.get_full_name(),
                    'email': student.email,
                },
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                },
                'statistics': {
                    'total_sessions': total,
                    'present': present,
                    'absent': absent,
                    'excused': excused,
                    'late': late,
                    'left_early': left_early,
                    'attendance_rate': round(attendance_rate, 2),
                }
            }
        except User.DoesNotExist:
            logger.error(f"Student {student_id} not found")
            raise
    
    @staticmethod
    def get_detailed_class_report(class_id, start_date=None, end_date=None):
        """
        Get detailed attendance report for a class.
        
        Args:
            class_id: ID of the class
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            Dictionary with detailed report including per-student breakdown
        """
        try:
            class_obj = Class.objects.get(id=class_id)
            
            # Get all enrolled students
            students = StudentEnrollment.objects.filter(
                class_ref=class_obj,
                is_active=True
            ).select_related('student')
            
            # Get attendance records
            records = AttendanceRecord.objects.filter(
                session__class_ref=class_obj
            )
            
            if start_date:
                records = records.filter(session__date__gte=start_date)
            if end_date:
                records = records.filter(session__date__lte=end_date)
            
            # Build report
            student_reports = []
            for enrollment in students:
                student = enrollment.student
                student_records = records.filter(student=student)
                
                total = student_records.count()
                present = student_records.filter(status__in=['present', 'late']).count()
                absent = student_records.filter(status='absent').count()
                excused = student_records.filter(status='excused').count()
                
                attendance_rate = (present / total * 100) if total > 0 else 0
                
                student_reports.append({
                    'student': {
                        'id': student.id,
                        'name': student.get_full_name(),
                        'email': student.email,
                    },
                    'statistics': {
                        'total_sessions': total,
                        'present': present,
                        'absent': absent,
                        'excused': excused,
                        'attendance_rate': round(attendance_rate, 2),
                    }
                })
            
            logger.info(f"Generated detailed class report for {class_id}")
            
            return {
                'class': {
                    'id': class_obj.id,
                    'code': class_obj.code,
                    'name': class_obj.name,
                    'instructor': class_obj.instructor.get_full_name(),
                },
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                },
                'student_reports': student_reports
            }
        except Class.DoesNotExist:
            logger.error(f"Class {class_id} not found")
            raise
    
    @staticmethod
    def get_session_attendance_report(session_id):
        """
        Get attendance report for a specific session.
        
        Args:
            session_id: ID of the session
        
        Returns:
            Dictionary with session attendance details
        """
        try:
            session = Session.objects.select_related('class_ref').get(id=session_id)
            
            # Get all enrolled students
            enrollments = StudentEnrollment.objects.filter(
                class_ref=session.class_ref,
                is_active=True
            ).select_related('student')
            
            # Get attendance records for this session
            attendance_map = {
                record.student_id: record
                for record in AttendanceRecord.objects.filter(session=session).select_related('student')
            }
            
            # Build report
            attendance_list = []
            for enrollment in enrollments:
                student = enrollment.student
                record = attendance_map.get(student.id)
                
                attendance_list.append({
                    'student': {
                        'id': student.id,
                        'name': student.get_full_name(),
                        'email': student.email,
                    },
                    'status': record.status if record else 'not_marked',
                    'check_in_time': record.check_in_time if record else None,
                    'check_out_time': record.check_out_time if record else None,
                    'notes': record.notes if record else '',
                })
            
            logger.info(f"Generated session attendance report for session {session_id}")
            
            return {
                'session': {
                    'id': session.id,
                    'class_code': session.class_ref.code,
                    'session_number': session.session_number,
                    'date': session.date,
                    'start_time': session.start_time,
                    'end_time': session.end_time,
                    'topic': session.topic,
                },
                'attendance': attendance_list,
                'summary': {
                    'total_students': len(attendance_list),
                    'present': sum(1 for a in attendance_list if a['status'] in ['present', 'late']),
                    'absent': sum(1 for a in attendance_list if a['status'] == 'absent'),
                    'not_marked': sum(1 for a in attendance_list if a['status'] == 'not_marked'),
                }
            }
        except Session.DoesNotExist:
            logger.error(f"Session {session_id} not found")
            raise


class ClassReportService:
    """Service for class-level reports."""
    
    @staticmethod
    def get_class_performance_report(class_id):
        """
        Get performance metrics for a class.
        
        Returns:
            Dictionary with class performance data
        """
        class_obj = Class.objects.get(id=class_id)
        
        # Enrollment metrics
        total_enrolled = StudentEnrollment.objects.filter(
            class_ref=class_obj,
            is_active=True
        ).count()
        
        # Session metrics
        total_sessions = Session.objects.filter(class_ref=class_obj).count()
        held_sessions = Session.objects.filter(
            class_ref=class_obj,
            is_held=True
        ).count()
        
        # Attendance metrics
        attendance_records = AttendanceRecord.objects.filter(
            session__class_ref=class_obj
        )
        
        total_attendance_entries = attendance_records.count()
        present_count = attendance_records.filter(
            status__in=['present', 'late']
        ).count()
        
        overall_rate = (present_count / total_attendance_entries * 100) if total_attendance_entries > 0 else 0
        
        logger.info(f"Generated class performance report for {class_id}")
        
        return {
            'class': {
                'id': class_obj.id,
                'code': class_obj.code,
                'name': class_obj.name,
            },
            'enrollment': {
                'total_enrolled': total_enrolled,
                'capacity': class_obj.capacity,
                'utilization_rate': round((total_enrolled / class_obj.capacity * 100), 2) if class_obj.capacity > 0 else 0,
            },
            'sessions': {
                'total': total_sessions,
                'held': held_sessions,
                'cancelled': total_sessions - held_sessions,
            },
            'attendance': {
                'total_entries': total_attendance_entries,
                'present': present_count,
                'overall_rate': round(overall_rate, 2),
            }
        }
