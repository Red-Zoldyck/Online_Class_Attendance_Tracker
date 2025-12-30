"""
Serializers for Attendance models.

Serializers:
- AttendanceRecordSerializer: Attendance record information
- AttendanceRecordDetailSerializer: Detailed attendance information
- BulkAttendanceSerializer: Bulk attendance marking
"""

from rest_framework import serializers
from apps.attendance.models import AttendanceRecord
from apps.users.serializers import UserSerializer
from apps.users.models import User
from apps.classes.models import Session


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceRecord model."""
    
    student = UserSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source='student',
        required=False
    )
    session_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Session.objects.all(),
        source='session',
        required=False
    )
    marked_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_late = serializers.ReadOnlyField()
    duration_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'student', 'student_id', 'session_id', 'status',
            'status_display', 'check_in_time', 'check_out_time',
            'duration_minutes', 'notes', 'marked_by', 'marked_at',
            'is_late', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'marked_at', 'created_at', 'updated_at', 'marked_by']


class AttendanceRecordDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for AttendanceRecord model."""
    
    student = UserSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source='student',
        required=False
    )
    session_details = serializers.SerializerMethodField()
    marked_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_late = serializers.ReadOnlyField()
    duration_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'student', 'student_id', 'session_details', 'status',
            'status_display', 'check_in_time', 'check_out_time',
            'duration_minutes', 'notes', 'marked_by', 'marked_at',
            'is_late', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'marked_at', 'created_at', 'updated_at', 'marked_by'
        ]
    
    def get_session_details(self, obj):
        """Get detailed session information."""
        from apps.classes.serializers import SessionSerializer
        return SessionSerializer(obj.session).data


class BulkAttendanceSerializer(serializers.Serializer):
    """
    Serializer for bulk attendance marking.
    
    Used for marking attendance for multiple students in a session.
    """
    
    session_id = serializers.IntegerField(
        required=True,
        help_text="Session ID"
    )
    attendances = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField(),
            help_text="Attendance record: {student_id, status, notes}"
        ),
        help_text="List of attendance records to create/update"
    )
    
    def validate_session_id(self, value):
        """Validate that session exists."""
        from apps.classes.models import Session
        try:
            Session.objects.get(id=value)
        except Session.DoesNotExist:
            raise serializers.ValidationError("Session not found.")
        return value
    
    def validate_attendances(self, value):
        """Validate attendance records."""
        for attendance in value:
            if 'student_id' not in attendance or 'status' not in attendance:
                raise serializers.ValidationError(
                    "Each attendance record must have student_id and status."
                )
            
            if attendance.get('status') not in dict(AttendanceRecord.AttendanceStatus.choices):
                raise serializers.ValidationError(
                    f"Invalid status: {attendance.get('status')}"
                )
        return value


def from_users_import(User):
    """Import User model."""
    from apps.users.models import User
    return User


def from_classes_import(Session):
    """Import Session model."""
    from apps.classes.models import Session
    return Session
