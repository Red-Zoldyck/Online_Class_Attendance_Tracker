# Development Guide - Online Class Attendance Tracker

## 1. Code Standards

### Python Style Guide

Follow PEP 8:
```bash
# Check code style
flake8 attendance_tracker/

# Auto-format code
black attendance_tracker/

# Sort imports
isort attendance_tracker/
```

### Code Organization

**Models** (`models.py`):
- One model per entity
- Clear docstrings
- Proper relationships
- Custom managers when needed

**Views** (`views.py`):
- ViewSets for API endpoints
- Class-based views for web
- Clear permission checks
- Proper error handling

**Serializers** (`serializers.py`):
- Input/output validation
- Field-level validation
- Custom validators
- Nested serializers for relationships

**Services** (`services.py`):
- Business logic separation
- Reusable functions
- Proper error handling
- Logging for important operations

---

## 2. Git Workflow

### Branch Naming

- `feature/feature-name` - New features
- `bugfix/bug-description` - Bug fixes
- `hotfix/issue-description` - Production hotfixes
- `docs/documentation-topic` - Documentation updates

### Commit Messages

```
[TYPE] Short description (50 chars max)

Detailed explanation (72 chars per line)

- Bullet point 1
- Bullet point 2

Fixes: #123 (if applicable)
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`

---

## 3. Testing Guide

### Unit Tests

Test individual components:

```python
# apps/users/tests.py
from django.test import TestCase
from apps.users.models import User

class UserTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_creation(self):
        self.assertTrue(self.user.id)
        self.assertEqual(self.user.email, 'test@example.com')
```

### Integration Tests

Test API endpoints:

```python
# apps/users/tests.py
from rest_framework.test import APITestCase
from rest_framework import status

class AuthAPITestCase(APITestCase):
    def test_user_registration(self):
        response = self.client.post('/api/v1/auth/register/', {
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'role': 3
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

---

## 4. Adding a New Feature

### Example: Add Email Notifications

1. **Create Migration**:
```bash
python manage.py makemigrations users --name add_email_notifications
```

2. **Update Model**:
```python
# apps/users/models.py
class User(AbstractUser):
    email_notifications = models.BooleanField(default=True)
    notification_frequency = models.CharField(
        max_length=20,
        choices=[
            ('instant', 'Instant'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly'),
        ],
        default='instant'
    )
```

3. **Create Service**:
```python
# apps/users/services/notification_service.py
class NotificationService:
    @staticmethod
    def send_attendance_notification(user, session):
        if not user.email_notifications:
            return
        
        # Send email logic here
        pass
```

4. **Update Views**:
```python
# Call service in attendance marking
def perform_create(self, serializer):
    instance = serializer.save()
    NotificationService.send_attendance_notification(
        instance.student, 
        instance.session
    )
```

5. **Create Tests**:
```python
def test_notification_sent_when_attendance_marked(self):
    # Test notification is sent
    pass
```

6. **Update Documentation**:
- Update API_REFERENCE.md
- Update SYSTEM_DOCUMENTATION.md
- Add code comments

---

## 5. Performance Optimization

### Database Optimization

```python
# Use select_related for ForeignKey
records = AttendanceRecord.objects.select_related(
    'student', 'session', 'marked_by'
)

# Use prefetch_related for reverse relationships
classes = Class.objects.prefetch_related('sessions')

# Use only() to select specific fields
users = User.objects.only('id', 'email', 'first_name')

# Use values() for aggregations
stats = AttendanceRecord.objects.values('status').annotate(
    count=Count('id')
)
```

### Caching

```python
from django.views.decorators.cache import cache_page
from django.core.cache import cache

# Cache view results
@cache_page(60 * 5)  # 5 minutes
def class_list(request):
    pass

# Manual caching
cache.set('class_stats', stats_data, 300)  # 5 minutes
stats = cache.get('class_stats')
```

### Query Optimization

```python
# Profile queries
python manage.py shell
from django.test.utils import override_settings
from django import db

with override_settings(DEBUG=True):
    records = AttendanceRecord.objects.all()
    list(records)
    
print(len(db.connection.queries))
```

---

## 6. Security Checklist

Before deploying:

- [ ] DEBUG = False
- [ ] SECRET_KEY is random (50+ chars)
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS/SSL enabled
- [ ] CSRF protection enabled
- [ ] SQL injection prevention (ORM only)
- [ ] XSS protection (template escaping)
- [ ] Input validation on all endpoints
- [ ] Rate limiting configured
- [ ] Database backups automated
- [ ] Logs properly configured
- [ ] Error details hidden from users
- [ ] Sensitive data in environment variables
- [ ] Database credentials secure
- [ ] API endpoints authenticated

---

## 7. Documentation Standards

### Code Comments

```python
def calculate_attendance_rate(self, class_id, start_date=None, end_date=None):
    """
    Calculate attendance rate for a class.
    
    This method calculates the percentage of students present
    in a given class during a specific time period.
    
    Args:
        class_id (int): ID of the class
        start_date (date, optional): Start date filter
        end_date (date, optional): End date filter
    
    Returns:
        float: Attendance rate as percentage (0-100)
    
    Raises:
        Class.DoesNotExist: If class not found
    
    Example:
        >>> rate = service.calculate_attendance_rate(
        ...     class_id=1,
        ...     start_date=date(2024, 1, 1)
        ... )
        >>> print(rate)
        85.5
    """
    pass
```

### API Documentation

```python
class UserListView(APIView):
    """
    User Management API.
    
    Endpoints for managing users:
    - GET: List all users (admin only)
    - POST: Create new user (admin only)
    """
    
    def get(self, request):
        """
        Get list of all users.
        
        Query Parameters:
        - role: Filter by role (admin, instructor, student)
        - is_active: Filter by active status (true/false)
        - search: Search by email or name
        
        Returns:
            Paginated list of users with status 200
        """
        pass
```

---

## 8. Debugging Guide

### Enable Debug Mode

```bash
# Set DEBUG=True in .env
DEBUG=True

# Run with verbose output
python manage.py runserver --verbosity=2
```

### View SQL Queries

```python
from django.db import connection, reset_queries
from django.conf import settings

settings.DEBUG = True

# Your code here
records = AttendanceRecord.objects.all()

for query in connection.queries:
    print(query['sql'])
```

### Use Python Debugger

```python
import pdb

def my_function():
    pdb.set_trace()  # Debugger will pause here
    # Continue debugging with commands:
    # l (list), n (next), s (step), c (continue)
    pass
```

### View Logs

```bash
# Follow logs in real-time
tail -f logs/attendance_tracker.log

# Filter logs
grep ERROR logs/attendance_tracker.log

# View last 50 lines
tail -n 50 logs/attendance_tracker.log
```

---

## 9. Common Tasks

### Add New API Endpoint

1. Create serializer in `serializers.py`
2. Create view/viewset in `views.py`
3. Add URL in `urls.py`
4. Write tests in `tests.py`
5. Document in `API_REFERENCE.md`

### Add New Permission

1. Create permission class in `permissions.py`
2. Add to `permission_classes` in views
3. Document in system documentation

### Add Database Migration

```bash
# Create migrations for changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create empty migration for data changes
python manage.py makemigrations --empty users --name add_field_description
```

---

## 10. Troubleshooting Development

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

### Database Errors

```bash
# Reset database (development only!)
python manage.py flush --no-input

# Check migrations
python manage.py showmigrations

# Fix migration conflicts
python manage.py makemigrations --merge
```

### Template Errors

```bash
# Check template syntax
python -m py_compile templates/users/login.html

# Clear cache
python manage.py clear_cache
```

---

**Last Updated**: December 30, 2024
