"""
Serializers for Class models.

Serializers:
- ClassSerializer: Basic class information
- ClassDetailSerializer: Detailed class information
- SessionSerializer: Session information
- StudentEnrollmentSerializer: Enrollment information
"""

from rest_framework import serializers
from apps.classes.models import Class, Session, StudentEnrollment, InstructorApplication
from apps.users.serializers import UserSerializer
from apps.users.models import User
from datetime import datetime, timedelta


class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model."""
    
    class_code = serializers.CharField(source='class_ref.code', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id', 'class_ref', 'class_code', 'session_number', 'date',
            'start_time', 'end_time', 'duration', 'topic', 'notes',
            'is_held', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_duration(self, obj):
        """Get session duration in minutes."""
        return obj.duration_minutes


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for StudentEnrollment model."""
    
    student = UserSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source='student',
        required=False
    )
    class_code = serializers.CharField(source='class_ref.code', read_only=True)
    
    class Meta:
        model = StudentEnrollment
        fields = [
            'id', 'student', 'student_id', 'class_ref', 'class_code',
            'enrollment_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrollment_date', 'created_at', 'updated_at']


class ClassSerializer(serializers.ModelSerializer):
    """Basic serializer for Class model."""
    
    instructor = UserSerializer(read_only=True)
    instructor_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source='instructor',
        required=False
    )
    enrolled_count = serializers.ReadOnlyField()
    available_slots = serializers.ReadOnlyField()
    is_ongoing = serializers.ReadOnlyField()
    session_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Class
        fields = [
            'id', 'code', 'name', 'description', 'instructor', 'instructor_id',
            'capacity', 'schedule', 'platform_url', 'is_active',
            'start_date', 'end_date', 'enrolled_count', 'available_slots',
            'session_count', 'is_ongoing', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_session_count(self, obj):
        """Get number of sessions for this class."""
        return obj.sessions.count()


class ClassDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Class model including related data."""
    
    instructor = UserSerializer(read_only=True)
    instructor_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source='instructor',
        required=False
    )
    sessions = SessionSerializer(many=True, read_only=True, source='sessions')
    enrolled_students = serializers.SerializerMethodField()
    enrolled_count = serializers.ReadOnlyField()
    available_slots = serializers.ReadOnlyField()
    is_ongoing = serializers.ReadOnlyField()
    
    class Meta:
        model = Class
        fields = [
            'id', 'code', 'name', 'description', 'instructor', 'instructor_id',
            'capacity', 'schedule', 'platform_url', 'is_active',
            'start_date', 'end_date', 'enrolled_count', 'available_slots',
            'is_ongoing', 'sessions', 'enrolled_students', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_enrolled_students(self, obj):
        """Get list of enrolled students."""
        enrollments = obj.students.filter(is_active=True)
        return StudentEnrollmentSerializer(enrollments, many=True).data


class InstructorApplicationSerializer(serializers.ModelSerializer):
    """Serializer for instructor applications."""

    instructor = UserSerializer(read_only=True)
    instructor_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='instructor',
        queryset=User.objects.all(),
        required=True
    )

    class Meta:
        model = InstructorApplication
        fields = [
            'id', 'class_ref', 'instructor', 'instructor_id', 'status', 'note',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'note', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at']


def from_users_import(User):
    """Import User model to avoid circular imports."""
    from apps.users.models import User
    return User


class QuickEnrollRequestSerializer(serializers.Serializer):
    """Minimal payload for instructor-led enrollment/creation of a student."""

    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
