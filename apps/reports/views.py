"""
@Red-Zoldyck - Online Class Attendance Tracker
Part of the Online Class Attendance Tracker system

Views for generating and viewing attendance reports.

Views:
- ClassAttendanceReportView: Generate class attendance reports
- StudentAttendanceReportView: Generate student attendance reports
- ExportReportView: Export reports to CSV/PDF
"""

from rest_framework import views, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.reports.services import (
    AttendanceReportService, ClassReportService
)
from apps.classes.models import Class, SectionCourse
from apps.attendance.models import AttendanceRecord
from apps.users.permissions import IsAdmin
from apps.classes.permissions import IsInstructorOrAdmin
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ClassAttendanceReportView(views.APIView):
    """
    Generate attendance report for a class.
    
    GET /api/v1/reports/class-report/?class_id=1&start_date=2024-01-01&end_date=2024-12-31
    """
    
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]
    
    def get(self, request):
        """Generate class attendance report."""
        class_id = request.query_params.get('class_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        detailed = request.query_params.get('detailed', '').lower() == 'true'
        
        if not class_id:
            return Response({
                'message': 'class_id parameter is required.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify access permission
            class_obj = Class.objects.get(id=class_id)
            if (class_obj.instructor != request.user and 
                request.user.role.name != 'admin'):
                return Response({
                    'message': 'You can only access reports for your classes.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Generate report
            if detailed:
                report = AttendanceReportService.get_detailed_class_report(
                    class_id, start_date, end_date
                )
            else:
                report = AttendanceReportService.get_class_attendance_summary(
                    class_id, start_date, end_date
                )
            
            logger.info(f"Class report generated for {class_id}")
            
            return Response({
                'report': report,
                'status': 'success'
            }, status=status.HTTP_200_OK)
        
        except Class.DoesNotExist:
            return Response({
                'message': 'Class not found.',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error generating class report: {str(e)}")
            return Response({
                'message': str(e),
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)


class StudentAttendanceReportView(views.APIView):
    """
    Generate attendance report for a student.
    
    GET /api/v1/reports/student-report/?student_id=1&class_id=1
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Generate student attendance report."""
        student_id = request.query_params.get('student_id')
        class_id = request.query_params.get('class_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not student_id:
            student_id = request.user.id
        
        try:
            # Students can only view their own reports
            if int(student_id) != request.user.id and request.user.role.name != 'admin':
                return Response({
                    'message': 'You can only view your own attendance report.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Generate report
            report = AttendanceReportService.get_student_attendance_summary(
                student_id, class_id, start_date, end_date
            )
            
            logger.info(f"Student report generated for {student_id}")
            
            return Response({
                'report': report,
                'status': 'success'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error generating student report: {str(e)}")
            return Response({
                'message': str(e),
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)


class ExportReportView(views.APIView):
    """
    Export attendance report to CSV.
    
    GET /api/v1/reports/export/?class_id=1&format=csv
    """
    
    permission_classes = [IsAuthenticated, IsInstructorOrAdmin]
    
    def get(self, request):
        """Export report to CSV format."""
        class_id = request.query_params.get('class_id')
        format_type = request.query_params.get('format', 'csv').lower()
        
        if not class_id:
            return Response({
                'message': 'class_id parameter is required.',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if format_type not in ['csv', 'pdf']:
            return Response({
                'message': 'Supported formats: csv, pdf',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify access
            class_obj = Class.objects.get(id=class_id)
            if (class_obj.instructor != request.user and 
                request.user.role.name != 'admin'):
                return Response({
                    'message': 'You can only export reports for your classes.',
                    'status': 'error'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Generate report
            report = AttendanceReportService.get_detailed_class_report(class_id)
            
            if format_type == 'csv':
                return self._export_csv(report, class_obj)
            else:
                return self._export_pdf(report, class_obj)
        
        except Class.DoesNotExist:
            return Response({
                'message': 'Class not found.',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @staticmethod
    def _export_csv(report, class_obj):
        """Export report to CSV format."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_{class_obj.code}_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Student Name', 'Email', 'Total Sessions', 'Present',
            'Absent', 'Excused', 'Attendance Rate (%)'
        ])
        
        # Write data
        for student_report in report['student_reports']:
            stats = student_report['statistics']
            writer.writerow([
                student_report['student']['name'],
                student_report['student']['email'],
                stats['total_sessions'],
                stats['present'],
                stats['absent'],
                stats['excused'],
                stats['attendance_rate']
            ])
        
        logger.info(f"Report exported to CSV for class {class_obj.code}")
        return response
    
    @staticmethod
    def _export_pdf(report, class_obj):
        """Export report to PDF format (requires reportlab)."""
        try:
            from reportlab.lib.pagesizes import letter, A4  # type: ignore
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer  # type: ignore
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
            from reportlab.lib.units import inch  # type: ignore
            from reportlab.lib import colors  # type: ignore
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#003366'),
                spaceAfter=30,
                alignment=1
            )
            elements.append(Paragraph(
                f"Attendance Report - {report['class']['code']} ({report['class']['name']})",
                title_style
            ))
            elements.append(Spacer(1, 0.3*inch))
            
            # Table data
            data = [['Student Name', 'Email', 'Total', 'Present', 'Absent', 'Excused', 'Rate (%)']]
            for student_report in report['student_reports']:
                stats = student_report['statistics']
                data.append([
                    student_report['student']['name'],
                    student_report['student']['email'],
                    str(stats['total_sessions']),
                    str(stats['present']),
                    str(stats['absent']),
                    str(stats['excused']),
                    f"{stats['attendance_rate']:.1f}%"
                ])
            
            # Create table
            table = Table(data, colWidths=[2*inch, 1.5*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="attendance_{report["class"]["code"]}_{datetime.now().strftime("%Y%m%d")}.pdf"'
            
            logger.info(f"Report exported to PDF for class {report['class']['code']}")
            return response
        
        except ImportError:
            logger.error("reportlab not installed. Install with: pip install reportlab")
            return HttpResponse(
                'PDF export requires reportlab library. Install with: pip install reportlab',
                status=501
            )


# Web Views (Django Templates)

class ClassReportView(LoginRequiredMixin, TemplateView):
    """View for displaying class attendance report."""
    template_name = 'reports/class_report.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        
        try:
            class_obj = Class.objects.get(id=class_id)
            
            # Verify access
            if (class_obj.instructor != self.request.user and 
                self.request.user.role.name != 'admin'):
                context['error'] = 'You do not have access to this report.'
                return context
            
            # Generate report
            report = AttendanceReportService.get_detailed_class_report(class_id)
            context['report'] = report
            context['class'] = class_obj
        
        except Class.DoesNotExist:
            context['error'] = 'Class not found.'
        
        return context


class ReportDashboardView(LoginRequiredMixin, TemplateView):
    """Web dashboard to view attendance reports grouped by section/course."""

    template_name = 'reports/attendance_dashboard.html'
    login_url = 'web-users:login'

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)

        if user.is_superuser or (role and role.name == 'admin'):
            return SectionCourse.objects.select_related('section__program', 'section__year_level', 'course', 'term', 'instructor').filter(is_active=True)
        if role and role.name == 'instructor':
            return SectionCourse.objects.select_related('section__program', 'section__year_level', 'course', 'term', 'instructor').filter(instructor=user, is_active=True)
        if role and role.name == 'student':
            return SectionCourse.objects.select_related('section__program', 'section__year_level', 'course', 'term', 'instructor').filter(enrollments__student=user, enrollments__is_active=True, is_active=True).distinct()
        return SectionCourse.objects.none()

    def _compute_stats(self, sc, start_date=None, end_date=None):
        class_code = f"ATT-SC-{sc.id}"  # shadow class code used for section-course attendance
        qs = AttendanceRecord.objects.filter(session__class_ref__code=class_code)
        if start_date:
            qs = qs.filter(session__date__gte=start_date)
        if end_date:
            qs = qs.filter(session__date__lte=end_date)

        total = qs.count()
        present = qs.filter(status__in=['present', 'late']).count()
        absent = qs.filter(status='absent').count()
        excused = qs.filter(status='excused').count()
        late = qs.filter(status='late').count()

        rate = (present / total * 100) if total else 0
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'excused': excused,
            'late': late,
            'attendance_rate': round(rate, 2),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date = self.request.GET.get('start_date') or None
        end_date = self.request.GET.get('end_date') or None
        section_course_id = self.request.GET.get('section_course')

        section_courses = self.get_queryset().order_by(
            'section__program__code', 'section__year_level__number', 'section__code', 'course__code'
        )

        # If a specific section-course is selected, show detailed records
        if section_course_id:
            try:
                sc = section_courses.get(id=section_course_id)
                class_code = f"ATT-SC-{sc.id}"
                records_qs = AttendanceRecord.objects.filter(
                    session__class_ref__code=class_code
                ).select_related('student', 'session')
                
                if start_date:
                    records_qs = records_qs.filter(session__date__gte=start_date)
                if end_date:
                    records_qs = records_qs.filter(session__date__lte=end_date)
                
                records_qs = records_qs.order_by('session__date', 'student__last_name', 'student__first_name')
                
                # Format status codes
                detailed_records = []
                for rec in records_qs:
                    status_map = {
                        'present': 'P',
                        'absent': 'A',
                        'late': 'L',
                        'excused': 'E',
                    }
                    detailed_records.append({
                        'student_name': rec.student.get_full_name() or rec.student.email,
                        'student_number': rec.student.student_number or '—',
                        'date': rec.session.date,
                        'status_code': status_map.get(rec.status, rec.status.upper()),
                        'status': rec.status,
                    })
                
                context['selected_section_course'] = sc
                context['detailed_records'] = detailed_records
                context['show_details'] = True
            except SectionCourse.DoesNotExist:
                pass
        
        # Always show summary for selection
        report_rows = []
        for sc in section_courses:
            stats = self._compute_stats(sc, start_date, end_date)
            report_rows.append({
                'section_course': sc,
                'section': sc.section,
                'course': sc.course,
                'term': sc.term,
                'instructor': sc.instructor,
                'schedule': sc.schedule,
                'stats': stats,
            })

        context['report_rows'] = report_rows
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['section_course_id'] = section_course_id
        return context
