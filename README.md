# Online Class Attendance Tracker

A production-ready Django web application for managing and tracking attendance in online classes.

## 🎯 Key Features

- **User Management**: Role-based access control (Admin, Instructor, Student)
- **Class Management**: Create and manage online classes with enrollment
- **Session Management**: Track individual class sessions
- **Attendance Tracking**: Mark and record student attendance
- **Real-time Reporting**: Generate attendance reports and analytics
- **RESTful API**: Complete REST API with JWT authentication
- **Web Interface**: User-friendly web dashboard
- **Security**: Comprehensive security features including JWT, CSRF protection, SQL injection prevention
- **Scalability**: Built for production deployment with optimization considerations

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- Git

### Installation

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

7. **Create Roles** (Optional - for initial setup):
```bash
python manage.py shell
from apps.users.models import Role
Role.objects.create(name='admin', display_name='Administrator', description='Full system access')
Role.objects.create(name='instructor', display_name='Instructor', description='Class and attendance management')
Role.objects.create(name='student', display_name='Student', description='View classes and attendance')
exit()
```

8. **Run Development Server**:
```bash
python manage.py runserver
```

Access the application at `http://localhost:8000`

---

## 📚 Documentation

- [System Documentation](./SYSTEM_DOCUMENTATION.md) - Complete system overview and architecture
- [API Reference](./API_REFERENCE.md) - API endpoints and usage examples
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment instructions
- [Database Schema](./ER_DIAGRAM.md) - Entity-relationship diagram (see below)

---

## 🏗️ System Architecture

### Technology Stack

**Backend**:
- Django 4.2 LTS
- Django REST Framework
- MySQL
- Celery (Task Queue)
- Redis (Caching)

**Frontend**:
- Django Templates
- Bootstrap 5
- JavaScript (ES6+)

**Infrastructure**:
- Gunicorn/Daphne
- Nginx
- Docker-compatible

### Application Structure

```
attendance_tracker/
├── config/              # Project configuration
├── apps/               # Django applications
│   ├── users/          # User authentication & management
│   ├── classes/        # Class and session management
│   ├── attendance/     # Attendance tracking
│   └── reports/        # Analytics and reporting
├── templates/          # HTML templates
├── static/             # CSS, JavaScript, images
├── services/           # Business logic
├── utils/              # Utility functions
└── tests/              # Unit and integration tests
```

---

## 🔐 Security Features

- **Authentication**: JWT tokens + session-based authentication
- **Authorization**: Role-Based Access Control (RBAC)
- **Password Security**: PBKDF2 hashing with complexity requirements
- **Login Protection**: Account lockout after 5 failed attempts
- **API Security**: CSRF protection, SQL injection prevention via ORM
- **HTTP Security**: Security headers (HSTS, CSP, X-Frame-Options)
- **Data Protection**: Secrets stored in .env, secure session cookies

---

## 📖 API Endpoints

### Authentication
```
POST   /api/v1/auth/register/       Register new user
POST   /api/v1/auth/login/          User login
POST   /api/v1/auth/logout/         User logout
POST   /api/v1/auth/token/refresh/  Refresh JWT token
```

### Classes
```
GET    /api/v1/classes/             List classes
POST   /api/v1/classes/             Create class
GET    /api/v1/classes/{id}/        Get class details
PUT    /api/v1/classes/{id}/        Update class
POST   /api/v1/classes/{id}/enroll_student/  Enroll student
```

### Attendance
```
GET    /api/v1/attendance/records/   List attendance
POST   /api/v1/attendance/records/   Create record
POST   /api/v1/attendance/bulk_mark/ Bulk mark attendance
GET    /api/v1/attendance/session_attendance/  Session attendance
GET    /api/v1/attendance/student_attendance/  Student attendance
```

### Reports
```
GET    /api/v1/reports/class-report/    Generate class report
GET    /api/v1/reports/student-report/  Generate student report
GET    /api/v1/reports/export/          Export to CSV/PDF
```

**API Documentation**: http://localhost:8000/api/v1/docs/swagger/

---

## 🗄️ Database Schema

### Main Entities

**User**: Custom user model with email authentication
- id, email, username, password, role_id, is_active, is_verified

**Role**: User roles (Admin, Instructor, Student)
- id, name, display_name, description, is_active

**Class**: Online class information
- id, code, name, instructor_id, capacity, start_date, end_date

**Session**: Individual class sessions
- id, class_id, date, start_time, end_time, topic, is_held

**StudentEnrollment**: Student enrollment records
- id, student_id, class_id, enrollment_date, is_active

**AttendanceRecord**: Individual attendance records
- id, student_id, session_id, status, check_in_time, check_out_time

All relationships enforce referential integrity with proper indexes.

---

## 👥 User Roles

### Administrator
- Full system access
- User management
- System configuration
- Access all reports

### Instructor
- Create and manage classes
- Create and manage sessions
- Mark attendance
- Generate class reports
- Manage student enrollments

### Student
- View enrolled classes
- View attendance records
- Download personal attendance reports
- Update profile information

---

## 🧪 Testing

Run all tests:
```bash
python manage.py test
```

Run specific app tests:
```bash
python manage.py test apps.users
python manage.py test apps.classes
python manage.py test apps.attendance
```

Run with coverage:
```bash
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 📊 Database Optimization

- Indexed frequently queried fields
- Proper use of select_related() and prefetch_related()
- Connection pooling (CONN_MAX_AGE=600)
- Query logging for performance analysis
- Pagination on all list endpoints

---

## 🐳 Docker Deployment (Optional)

```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

---

## 📝 Logging

Logs are stored in `logs/attendance_tracker.log`:

```python
# View logs
tail -f logs/attendance_tracker.log

# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## ⚙️ Configuration

Edit `.env` file to configure:

```env
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=mysql://user:password@host:3306/db
ALLOWED_HOSTS=yourdomain.com
```

---

## 🔍 Admin Interface

Access Django admin at: `http://localhost:8000/admin`

Manage:
- Users and roles
- Classes and sessions
- Attendance records
- User profiles

---

## 🚀 Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for production deployment instructions including:
- Nginx configuration
- Gunicorn setup
- SSL/TLS certificates
- Database backups
- Performance tuning

---

## 📞 Support & Troubleshooting

### Common Issues

**Database Connection Error**:
- Verify MySQL is running
- Check database credentials in `.env`

**Static Files Not Loading**:
- Run `python manage.py collectstatic`
- Verify STATIC_URL in settings

**Import Errors**:
- Run `pip install -r requirements.txt`
- Verify virtual environment is activated

For more help, check:
- [Django Documentation](https://docs.djangoproject.com/)
- [DRF Documentation](https://www.django-rest-framework.org/)
- System logs in `logs/attendance_tracker.log`

---

## 📄 License

This project is built with best practices for production systems.

---

## ✅ Development Standards Met

- ✅ Django Best Practices & MTV Architecture
- ✅ RESTful API Design
- ✅ Role-Based Access Control (RBAC)
- ✅ Comprehensive Security Implementation
- ✅ Proper Database Normalization (3NF)
- ✅ Clean Code & Modular Architecture
- ✅ Extensive Documentation
- ✅ Production-Ready Configuration
- ✅ Error Handling & Logging
- ✅ Performance Optimization

---

## 📅 Version

**Version**: 1.0.0  
**Last Updated**: December 30, 2024  
**Python**: 3.10+  
**Django**: 4.2 LTS  

---

**For complete documentation, see [SYSTEM_DOCUMENTATION.md](./SYSTEM_DOCUMENTATION.md)**
