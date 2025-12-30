# Online Class Attendance Tracker - System Documentation

## 1. Project Overview

The **Online Class Attendance Tracker** is a production-ready Django web application designed to streamline attendance management for online classes. The system addresses critical challenges in remote learning environments:

- **Manual Attendance Errors**: Automated, accurate attendance recording
- **Poor Attendance Monitoring**: Real-time tracking and reporting
- **Inconsistent Record Keeping**: Centralized database with standardized formats

### Target Users

1. **System Administrator**: Overall system management, user management, data integrity
2. **Instructor**: Class management, attendance marking, report generation
3. **Student**: View attendance records, verify enrollment

---

## 2. Technology Stack

### Backend
- **Framework**: Django 4.2 (LTS)
- **API**: Django REST Framework (DRF)
- **Database**: MySQL 8.0+
- **Authentication**: JWT (JSON Web Tokens) + Session-based
- **Task Queue**: Celery with Redis

### Frontend
- **Templates**: Django Templates (HTML5)
- **Styling**: Bootstrap 5
- **Client-side**: Vanilla JavaScript
- **HTTP Client**: Fetch API

### Infrastructure
- **Server**: Gunicorn/Daphne
- **Caching**: Redis
- **Task Queue**: Celery Beat
- **Logging**: Python logging module

---

## 3. System Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────┐
│         Presentation Layer (UI/Templates)       │
│  - Django Templates (HTML5, CSS, JavaScript)    │
│  - REST API Endpoints (JSON responses)          │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│    Application Layer (Views & ViewSets)         │
│  - Class-based Views (CBV)                      │
│  - ViewSets (DRF)                               │
│  - Serializers (data validation & transformation)│
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│    Business Logic Layer (Services)              │
│  - ReportService (analytics & reporting)        │
│  - AttendanceService (attendance logic)         │
│  - AuthenticationService (auth logic)           │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│     Security Layer (Auth & Permissions)         │
│  - JWT Authentication                           │
│  - Role-Based Access Control (RBAC)             │
│  - Permission Classes                           │
│  - Middleware (security headers)                │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│      Data Layer (Models & ORM)                  │
│  - Django ORM Models                            │
│  - Database Migrations                          │
│  - Query Optimization (prefetch_related, etc)   │
└─────────────────────────────────────────────────┘
```

### Data Flow

```
User Request (Web/API)
        ↓
URL Router (urls.py)
        ↓
View/ViewSet
        ↓
Serializer (validation & transformation)
        ↓
Service Layer (business logic)
        ↓
ORM Models (database queries)
        ↓
Database (MySQL)
        ↓
Response (JSON/HTML)
```

---

## 4. Database Schema (3NF)

### Entities & Relationships

#### User (Custom Django User)
```
- id (PK)
- email (UNIQUE)
- username (UNIQUE)
- first_name
- last_name
- password (hashed)
- phone_number
- role_id (FK → Role)
- is_active
- is_verified
- profile_picture
- last_login_ip
- login_attempts
- locked_until
- created_at
- updated_at
```

#### Role
```
- id (PK)
- name (UNIQUE) - admin, instructor, student
- display_name
- description
- is_active
- created_at
- updated_at
```

#### Class
```
- id (PK)
- code (UNIQUE) - CS101, MATH201, etc.
- name
- description
- instructor_id (FK → User)
- capacity
- schedule
- platform_url
- is_active
- start_date
- end_date
- created_at
- updated_at
```

#### Session
```
- id (PK)
- class_id (FK → Class)
- session_number
- date
- start_time
- end_time
- topic
- notes
- is_held
- created_at
- updated_at
- UNIQUE(class_id, date, start_time)
```

#### StudentEnrollment
```
- id (PK)
- student_id (FK → User)
- class_id (FK → Class)
- enrollment_date
- is_active
- created_at
- updated_at
- UNIQUE(student_id, class_id)
```

#### AttendanceRecord
```
- id (PK)
- student_id (FK → User)
- session_id (FK → Session)
- status (present, absent, late, excused, left_early)
- check_in_time
- check_out_time
- notes
- marked_by_id (FK → User)
- marked_at
- created_at
- updated_at
- UNIQUE(student_id, session_id)
```

#### UserProfile
```
- user_id (PK, FK → User, OneToOne)
- department
- bio
- website
- social_media (JSON)
- created_at
- updated_at
```

### Indexes for Performance

- `User(email, role_id, is_active, created_at)`
- `Class(code, instructor_id, is_active)`
- `Session(class_id, date)`
- `StudentEnrollment(student_id, class_id, is_active)`
- `AttendanceRecord(student_id, session_id, status, marked_at)`

---

## 5. Project Folder Structure

```
attendance_tracker/
│
├── config/                          # Project settings
│   ├── __init__.py
│   ├── settings.py                  # Django settings
│   ├── urls.py                      # URL routing
│   ├── wsgi.py                      # WSGI application
│   ├── asgi.py                      # ASGI application
│   └── celery.py                    # Celery configuration
│
├── apps/                            # Django applications
│   ├── __init__.py
│   │
│   ├── users/                       # User management
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                # User, Role, UserProfile
│   │   ├── views.py                 # Authentication views
│   │   ├── serializers.py           # User serializers
│   │   ├── permissions.py           # Auth permissions
│   │   ├── admin.py                 # Django admin configuration
│   │   ├── middleware.py            # Security middleware
│   │   ├── urls.py                  # API URLs
│   │   ├── urls_web.py              # Web interface URLs
│   │   └── tests.py                 # Unit tests
│   │
│   ├── classes/                     # Class management
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                # Class, Session, StudentEnrollment
│   │   ├── views.py                 # Class and session views
│   │   ├── serializers.py           # Class serializers
│   │   ├── permissions.py           # Class permissions
│   │   ├── admin.py                 # Django admin configuration
│   │   ├── urls.py                  # API URLs
│   │   ├── urls_web.py              # Web interface URLs
│   │   └── tests.py                 # Unit tests
│   │
│   ├── attendance/                  # Attendance management
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                # AttendanceRecord
│   │   ├── views.py                 # Attendance views
│   │   ├── serializers.py           # Attendance serializers
│   │   ├── admin.py                 # Django admin configuration
│   │   ├── urls.py                  # API URLs
│   │   ├── urls_web.py              # Web interface URLs
│   │   └── tests.py                 # Unit tests
│   │
│   └── reports/                     # Reporting & Analytics
│       ├── __init__.py
│       ├── apps.py
│       ├── services.py              # Report generation logic
│       ├── views.py                 # Report views
│       ├── urls.py                  # API URLs
│       └── tests.py                 # Unit tests
│
├── templates/                       # Django templates
│   ├── base.html                    # Base template
│   ├── errors/
│   │   ├── 404.html
│   │   └── 500.html
│   ├── users/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── dashboard.html
│   ├── classes/
│   │   ├── class_list.html
│   │   ├── class_detail.html
│   │   └── class_form.html
│   ├── attendance/
│   │   ├── mark_attendance.html
│   │   └── student_attendance.html
│   └── reports/
│       ├── class_report.html
│       └── student_report.html
│
├── static/                          # Static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/
│       └── logo.png
│
├── services/                        # Business logic services
│   ├── attendance_service.py
│   ├── class_service.py
│   └── notification_service.py
│
├── utils/                           # Utility functions
│   ├── decorators.py
│   ├── validators.py
│   └── helpers.py
│
├── tests/                           # Integration tests
│   ├── test_users.py
│   ├── test_classes.py
│   ├── test_attendance.py
│   └── test_reports.py
│
├── logs/                            # Application logs
│   └── attendance_tracker.log
│
├── manage.py                        # Django management script
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── README.md                        # Project README
└── DEPLOYMENT.md                    # Deployment guide
```

### Folder Purpose Reference

| Folder | Purpose |
|--------|---------|
| `config/` | Django project configuration, URL routing, WSGI/ASGI setup |
| `apps/` | Modular Django applications organized by feature |
| `templates/` | HTML templates for web interface |
| `static/` | CSS, JavaScript, images for frontend |
| `services/` | Business logic layer (separated from views) |
| `utils/` | Reusable utility functions and decorators |
| `tests/` | Integration and unit tests |
| `logs/` | Application log files (auto-created) |

---

## 6. API Endpoints

### Authentication Endpoints

```
POST   /api/v1/auth/register/        Register new user
POST   /api/v1/auth/login/           User login
POST   /api/v1/auth/logout/          User logout
POST   /api/v1/auth/token/refresh/   Refresh JWT token
```

### User Management (Admin Only)

```
GET    /api/v1/users/                List all users
POST   /api/v1/users/                Create new user
GET    /api/v1/users/{id}/           Get user details
PUT    /api/v1/users/{id}/           Update user
DELETE /api/v1/users/{id}/           Delete user
GET    /api/v1/users/me/             Get current user
POST   /api/v1/users/{id}/change_password/  Change password
```

### Class Management

```
GET    /api/v1/classes/              List classes
POST   /api/v1/classes/              Create class (instructor/admin)
GET    /api/v1/classes/{id}/         Get class details
PUT    /api/v1/classes/{id}/         Update class
DELETE /api/v1/classes/{id}/         Delete class
POST   /api/v1/classes/{id}/enroll_student/  Enroll student
GET    /api/v1/classes/{id}/students/       Get enrolled students
```

### Session Management

```
GET    /api/v1/sessions/             List sessions
POST   /api/v1/sessions/             Create session
GET    /api/v1/sessions/{id}/        Get session details
PUT    /api/v1/sessions/{id}/        Update session
DELETE /api/v1/sessions/{id}/        Delete session
```

### Attendance Management

```
GET    /api/v1/attendance/records/           List attendance records
POST   /api/v1/attendance/records/           Create attendance record
GET    /api/v1/attendance/records/{id}/      Get attendance details
PUT    /api/v1/attendance/records/{id}/      Update attendance
POST   /api/v1/attendance/mark_attendance/   Mark single attendance
POST   /api/v1/attendance/bulk_mark/         Bulk mark attendance
GET    /api/v1/attendance/session_attendance/ Get session attendance
GET    /api/v1/attendance/student_attendance/ Get student attendance
```

### Reports

```
GET    /api/v1/reports/class-report/    Generate class report
GET    /api/v1/reports/student-report/  Generate student report
GET    /api/v1/reports/export/          Export report (CSV/PDF)
```

---

## 7. Security Implementation

### Authentication & Authorization

1. **Custom User Model**: Extended Django User with additional fields
2. **JWT Tokens**: Stateless authentication for APIs
3. **Session-based Auth**: Traditional sessions for web interface
4. **RBAC (Role-Based Access Control)**: Three roles - Admin, Instructor, Student

### Security Features

1. **Password Security**:
   - PBKDF2 hashing (Django default)
   - Minimum 8 characters
   - Complexity requirements

2. **Login Security**:
   - Account lockout after 5 failed attempts (30 minutes)
   - Login attempt tracking
   - IP address logging

3. **API Security**:
   - CSRF protection for state-changing requests
   - SQL injection prevention (Django ORM)
   - XSS protection via template escaping

4. **HTTP Security Headers**:
   - X-Frame-Options: DENY
   - X-Content-Type-Options: nosniff
   - Content-Security-Policy
   - Strict-Transport-Security

5. **Data Protection**:
   - Sensitive data in .env file
   - Password hashing
   - Secure session cookies (HttpOnly, Secure, SameSite)

---

## 8. Development Environment Setup

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- Redis (optional, for caching)
- Git

### Installation Steps

1. **Clone and Navigate**:
```bash
cd "path/to/Online Class Attendance Tracker/Version 1"
```

2. **Create Virtual Environment**:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

3. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure Environment**:
```bash
copy .env.example .env
# Edit .env with your database credentials
```

5. **Run Migrations**:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create Superuser**:
```bash
python manage.py createsuperuser
```

7. **Create Roles** (run in Django shell):
```bash
python manage.py shell
from apps.users.models import Role
Role.objects.create(name='admin', display_name='Administrator', description='Full system access')
Role.objects.create(name='instructor', display_name='Instructor', description='Class management and attendance')
Role.objects.create(name='student', display_name='Student', description='View classes and attendance')
exit()
```

8. **Collect Static Files**:
```bash
python manage.py collectstatic --noinput
```

9. **Run Development Server**:
```bash
python manage.py runserver
```

Access the application at `http://localhost:8000`

---

## 9. API Documentation

Complete API documentation is available at:
- Swagger UI: `http://localhost:8000/api/v1/docs/swagger/`
- ReDoc: `http://localhost:8000/api/v1/docs/redoc/`

---

## 10. Testing

### Run Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.users
python manage.py test apps.classes
python manage.py test apps.attendance

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 11. Logging

Logs are stored in `logs/attendance_tracker.log`:

- **INFO**: Normal application events
- **WARNING**: Warning messages (e.g., account lockouts)
- **ERROR**: Error messages and exceptions

Configure logging level in `config/settings.py`

---

## 12. Performance Optimization

### Database Optimization

1. **Query Optimization**:
   - Use `select_related()` for ForeignKey relationships
   - Use `prefetch_related()` for reverse relationships
   - Use database indexes on frequently queried fields

2. **Caching**:
   - Redis-based caching for class lists
   - Session caching for user authentication

### Code Optimization

1. **Pagination**: All list endpoints support pagination
2. **Filtering**: Filter by role, status, date ranges
3. **Lazy Loading**: QuerySets are lazy-evaluated

---

## 13. Maintenance & Scalability

### Monitoring

- View error logs in `/logs/` directory
- Monitor Django admin interface
- Check database query performance

### Scalability Considerations

1. Separate database server
2. Use Gunicorn with multiple workers
3. Implement Redis caching layer
4. Use Celery for async tasks
5. Load balancing with Nginx

---

## 14. Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Verify MySQL is running
   - Check database credentials in `.env`
   - Ensure database exists

2. **Import Errors**:
   - Run `pip install -r requirements.txt`
   - Verify virtual environment is activated

3. **Static Files Not Loading**:
   - Run `python manage.py collectstatic`
   - Check STATIC_URL and STATIC_ROOT in settings

---

## 15. Support & Contact

For issues or questions:
- Check Django documentation: https://docs.djangoproject.com/
- Check DRF documentation: https://www.django-rest-framework.org/
- Review application logs

---

**Last Updated**: December 30, 2024
**Version**: 1.0.0
