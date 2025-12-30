# API Reference - Online Class Attendance Tracker

## Base URL

```
http://localhost:8000/api/v1/
```

## Authentication

All endpoints except `auth/register/` and `auth/login/` require authentication.

### JWT Token Authentication

Include the token in request header:

```
Authorization: Bearer <access_token>
```

### Example Request

```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
     http://localhost:8000/api/v1/users/me/
```

---

## Authentication Endpoints

### Register User

**Endpoint**: `POST /api/v1/auth/register/`

**Request Body**:
```json
{
  "email": "student@example.com",
  "username": "student123",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "phone_number": "+1234567890",
  "role": 3
}
```

**Response** (201 Created):
```json
{
  "message": "User registered successfully. Please log in.",
  "user": {
    "id": 5,
    "email": "student@example.com",
    "username": "student123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "role": {
      "id": 3,
      "name": "student",
      "display_name": "Student"
    },
    "is_verified": false,
    "is_active": true
  },
  "status": "success"
}
```

---

### Login User

**Endpoint**: `POST /api/v1/auth/login/`

**Request Body**:
```json
{
  "email": "instructor@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "message": "Login successful.",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 2,
    "email": "instructor@example.com",
    "username": "instructor1",
    "first_name": "Jane",
    "last_name": "Smith",
    "role": {
      "id": 2,
      "name": "instructor",
      "display_name": "Instructor"
    }
  },
  "status": "success"
}
```

---

### Get Current User

**Endpoint**: `GET /api/v1/users/me/`

**Response** (200 OK):
```json
{
  "id": 2,
  "email": "instructor@example.com",
  "username": "instructor1",
  "first_name": "Jane",
  "last_name": "Smith",
  "phone_number": "+1234567890",
  "role": {
    "id": 2,
    "name": "instructor",
    "display_name": "Instructor"
  },
  "is_verified": true,
  "is_active": true
}
```

---

## Class Management Endpoints

### List Classes

**Endpoint**: `GET /api/v1/classes/`

**Query Parameters**:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `is_active`: Filter by active status (true/false)
- `instructor`: Filter by instructor ID
- `search`: Search by code or name
- `ordering`: Order by field (-created_at, -start_date, name)

**Response** (200 OK):
```json
{
  "count": 5,
  "next": "http://localhost:8000/api/v1/classes/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "CS101",
      "name": "Introduction to Computer Science",
      "description": "Basic CS concepts",
      "instructor": {
        "id": 2,
        "email": "instructor@example.com",
        "first_name": "Jane",
        "last_name": "Smith"
      },
      "capacity": 50,
      "schedule": "Mon/Wed 10:00 AM",
      "is_active": true,
      "start_date": "2024-01-15",
      "end_date": "2024-05-15",
      "enrolled_count": 35,
      "available_slots": 15,
      "session_count": 24,
      "is_ongoing": true,
      "created_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

---

### Get Class Details

**Endpoint**: `GET /api/v1/classes/{id}/`

**Response** (200 OK):
```json
{
  "id": 1,
  "code": "CS101",
  "name": "Introduction to Computer Science",
  "instructor": {
    "id": 2,
    "email": "instructor@example.com"
  },
  "capacity": 50,
  "enrolled_count": 35,
  "sessions": [
    {
      "id": 1,
      "class_ref": 1,
      "class_code": "CS101",
      "session_number": 1,
      "date": "2024-01-15",
      "start_time": "10:00:00",
      "end_time": "11:30:00",
      "duration": 90,
      "topic": "Introduction and Overview"
    }
  ],
  "enrolled_students": [
    {
      "id": 1,
      "student": {
        "id": 5,
        "email": "student@example.com",
        "first_name": "John",
        "last_name": "Doe"
      },
      "class_ref": 1,
      "enrollment_date": "2024-01-10T15:30:00Z"
    }
  ]
}
```

---

### Create Class (Instructor/Admin Only)

**Endpoint**: `POST /api/v1/classes/`

**Request Body**:
```json
{
  "code": "MATH201",
  "name": "Calculus I",
  "description": "Differential calculus",
  "capacity": 40,
  "schedule": "Tue/Thu 2:00 PM",
  "platform_url": "https://zoom.us/my/classroom",
  "is_active": true,
  "start_date": "2024-02-01",
  "end_date": "2024-05-30"
}
```

**Response** (201 Created):
```json
{
  "id": 2,
  "code": "MATH201",
  "name": "Calculus I",
  "instructor": {
    "id": 2,
    "email": "instructor@example.com"
  },
  "capacity": 40,
  "enrolled_count": 0,
  "available_slots": 40,
  "is_active": true,
  "created_at": "2024-01-20T12:00:00Z"
}
```

---

### Enroll Student in Class

**Endpoint**: `POST /api/v1/classes/{id}/enroll_student/`

**Request Body**:
```json
{
  "student_id": 5
}
```

**Response** (201 Created):
```json
{
  "message": "Student enrolled successfully.",
  "enrollment": {
    "id": 1,
    "student": {
      "id": 5,
      "email": "student@example.com",
      "first_name": "John"
    },
    "class_ref": 1,
    "enrollment_date": "2024-01-20T15:30:00Z",
    "is_active": true
  },
  "status": "success"
}
```

---

## Attendance Management Endpoints

### Mark Attendance

**Endpoint**: `POST /api/v1/attendance/records/mark_attendance/`

**Request Body**:
```json
{
  "student_id": 5,
  "session_id": 1,
  "status": "present",
  "check_in_time": "2024-01-15T10:05:00Z",
  "check_out_time": "2024-01-15T11:35:00Z",
  "notes": "Attended full session"
}
```

**Response** (201 Created):
```json
{
  "message": "Attendance marked successfully.",
  "attendance": {
    "id": 1,
    "student": {
      "id": 5,
      "email": "student@example.com"
    },
    "status": "present",
    "status_display": "Present",
    "check_in_time": "2024-01-15T10:05:00Z",
    "check_out_time": "2024-01-15T11:35:00Z",
    "duration_minutes": 90,
    "is_late": false,
    "notes": "Attended full session"
  },
  "status": "success"
}
```

---

### Bulk Mark Attendance

**Endpoint**: `POST /api/v1/attendance/records/bulk_mark/`

**Request Body**:
```json
{
  "session_id": 1,
  "attendances": [
    {
      "student_id": 5,
      "status": "present",
      "notes": ""
    },
    {
      "student_id": 6,
      "status": "absent",
      "notes": "No notification"
    },
    {
      "student_id": 7,
      "status": "late",
      "notes": "Connection issues"
    }
  ]
}
```

**Response** (201 Created):
```json
{
  "message": "Attendance marked for 3 students.",
  "count": 3,
  "status": "success"
}
```

---

### Get Session Attendance

**Endpoint**: `GET /api/v1/attendance/records/session_attendance/?session_id=1`

**Response** (200 OK):
```json
{
  "session": 1,
  "records": [
    {
      "id": 1,
      "student": {
        "id": 5,
        "email": "student@example.com"
      },
      "status": "present",
      "status_display": "Present",
      "check_in_time": "2024-01-15T10:05:00Z",
      "check_out_time": "2024-01-15T11:35:00Z"
    }
  ],
  "status": "success"
}
```

---

### Get Student Attendance

**Endpoint**: `GET /api/v1/attendance/records/student_attendance/?student_id=5`

**Response** (200 OK):
```json
{
  "student": "John Doe",
  "total_sessions": 10,
  "present": 8,
  "absent": 1,
  "excused": 1,
  "attendance_rate": 80.0,
  "records": [
    {
      "id": 1,
      "status": "present",
      "check_in_time": "2024-01-15T10:05:00Z"
    }
  ],
  "status": "success"
}
```

---

## Reports Endpoints

### Generate Class Report

**Endpoint**: `GET /api/v1/reports/class-report/?class_id=1&detailed=true`

**Query Parameters**:
- `class_id` (required): ID of the class
- `start_date` (optional): Start date filter (YYYY-MM-DD)
- `end_date` (optional): End date filter (YYYY-MM-DD)
- `detailed` (optional): true for detailed report with student breakdown

**Response** (200 OK):
```json
{
  "report": {
    "class": {
      "id": 1,
      "code": "CS101",
      "name": "Introduction to Computer Science",
      "instructor": "Jane Smith"
    },
    "student_reports": [
      {
        "student": {
          "id": 5,
          "name": "John Doe",
          "email": "student@example.com"
        },
        "statistics": {
          "total_sessions": 10,
          "present": 8,
          "absent": 1,
          "excused": 1,
          "attendance_rate": 80.0
        }
      }
    ]
  },
  "status": "success"
}
```

---

### Generate Student Report

**Endpoint**: `GET /api/v1/reports/student-report/?student_id=5&class_id=1`

**Query Parameters**:
- `student_id` (optional): Student ID (defaults to current user)
- `class_id` (optional): Filter to specific class
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Response** (200 OK):
```json
{
  "report": {
    "student": {
      "id": 5,
      "name": "John Doe",
      "email": "student@example.com"
    },
    "statistics": {
      "total_sessions": 30,
      "present": 24,
      "absent": 4,
      "excused": 2,
      "late": 3,
      "left_early": 1,
      "attendance_rate": 80.0
    }
  },
  "status": "success"
}
```

---

### Export Report to CSV

**Endpoint**: `GET /api/v1/reports/export/?class_id=1&format=csv`

**Query Parameters**:
- `class_id` (required): Class ID
- `format` (optional): csv or pdf (default: csv)

**Response**: Binary file download

---

## Error Responses

### 400 Bad Request

```json
{
  "message": "Invalid input data",
  "status": "error"
}
```

### 401 Unauthorized

```json
{
  "message": "Invalid email or password.",
  "status": "error"
}
```

### 403 Forbidden

```json
{
  "message": "You do not have permission to access this resource.",
  "status": "error"
}
```

### 404 Not Found

```json
{
  "message": "Resource not found.",
  "status": "error"
}
```

### 500 Internal Server Error

```json
{
  "message": "An error occurred processing your request.",
  "status": "error"
}
```

---

**Last Updated**: December 30, 2024
