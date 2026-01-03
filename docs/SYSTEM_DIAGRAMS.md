# System Diagrams - Online Class Attendance Tracker

## 1. Data Flow Diagram (DFD)

### Level 0 - Context Diagram

```
                          ┌─────────────────────────┐
                          │  Attendance Tracker     │
                          │      System             │
                          └─────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
          ┌──────────┐        ┌──────────┐        ┌──────────┐
          │ Students │        │Instructors│       │  Admin   │
          └──────────┘        └──────────┘        └──────────┘
                │                   │                   │
    ┌───────────┴──────────┐        │        ┌─────────┴────────┐
    │                      │        │        │                  │
    │  View classes &      │        │        │  System admin    │
    │  attendance records  │  Mark attendance  Configuration    │
    │                      │  Create classes   │                │
    │                      │  Create sessions  │                │
    └──────────────────────┘        │        └──────────────────┘
                                    │
                            ┌───────▼────────┐
                            │   Database     │
                            │   (MySQL)      │
                            └────────────────┘
```

### Level 1 - Process Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Module (1.0)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1.1 Registration  │ 1.2 Login   │ 1.3 Profile Mgmt      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Class Module (2.0)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 2.1 Create      │ 2.2 Manage    │ 2.3 Enroll Students   │  │
│  │ Classes         │ Sessions      │                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Attendance Module (3.0)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3.1 Mark        │ 3.2 Record    │ 3.3 View Records      │  │
│  │ Attendance      │ Check-in/out  │                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Reports Module (4.0)                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4.1 Generate    │ 4.2 Student   │ 4.3 Export Reports    │  │
│  │ Class Report    │ Reports       │ (CSV/PDF)             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Entity Relationship Diagram (ERD)

### Logical Data Model

```
┌──────────────────┐
│      Role        │
├──────────────────┤
│ id (PK)          │
│ name (UNIQUE)    │
│ display_name     │
│ description      │
│ is_active        │
│ created_at       │
│ updated_at       │
└────────┬─────────┘
         │ 1:N
         │
         ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│        User              │      │    UserProfile           │
├──────────────────────────┤      ├──────────────────────────┤
│ id (PK)                  │◄────►│ user_id (PK, FK)         │
│ email (UNIQUE)           │ 1:1  │ department               │
│ username (UNIQUE)        │      │ bio                      │
│ password (hashed)        │      │ website                  │
│ first_name               │      │ social_media (JSON)      │
│ last_name                │      │ created_at               │
│ phone_number             │      │ updated_at               │
│ role_id (FK)             │      └──────────────────────────┘
│ is_active                │
│ is_verified              │
│ profile_picture          │
│ last_login_ip            │
│ login_attempts           │
│ locked_until             │
│ created_at               │
│ updated_at               │
└────────┬────────────────┬┘
         │                │
      1:N│                │1:N
         │                │
         │        ┌───────┴────────┐
         │        │                │
         │        ▼                ▼
         │   ┌──────────────┐  ┌─────────────────┐
         │   │    Class     │  │ StudentEnrollment│
         │   ├──────────────┤  ├─────────────────┤
         │   │ id (PK)      │  │ id (PK)         │
         │   │ code (UNIQUE)│  │ student_id (FK) │
         │   │ name         │  │ class_id (FK)   │
         │   │ description  │  │ enrollment_date │
         │   │ instructor_id├─ │ is_active       │
         │   │ capacity     │  │ created_at      │
         │   │ schedule     │  │ updated_at      │
         │   │ platform_url │  └────────┬────────┘
         │   │ is_active    │           │ 1:N
         │   │ start_date   │           │
         │   │ end_date     │           │
         │   │ created_at   │       ┌───▼──────────────┐
         │   │ updated_at   │       │ AttendanceRecord │
         │   └────────┬─────┘       ├──────────────────┤
         │            │             │ id (PK)          │
         │        1:N │             │ student_id (FK)  │
         │            │             │ session_id (FK)  │
         │            ▼             │ status           │
         │       ┌──────────────┐   │ check_in_time    │
         │       │   Session    │   │ check_out_time   │
         │       ├──────────────┤   │ notes            │
         │       │ id (PK)      │   │ marked_by_id (FK)│
         │       │ class_id (FK)├──►│ marked_at        │
         │       │ session_no   │   │ created_at       │
         │       │ date         │   │ updated_at       │
         │       │ start_time   │   └──────────────────┘
         │       │ end_time     │
         │       │ topic        │
         │       │ notes        │
         │       │ is_held      │
         │       │ created_at   │
         │       │ updated_at   │
         │       └──────────────┘
         │
         └─ marked_by_id (FK) ─►[References Self]
```

---

## 3. UML Use Case Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  Attendance Tracker System                       │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Student    │    │  Instructor  │    │     Admin    │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         │   ┌──────────────────────────────┐   │               │
│         ├──►│   Register / Login           │◄──┤               │
│         │   └──────────────────────────────┘   │               │
│         │                                       │               │
│         │   ┌──────────────────────────────┐   │               │
│         ├──►│   View Enrolled Classes       │   │               │
│         │   └──────────────────────────────┘   │               │
│         │                                       │               │
│         │   ┌──────────────────────────────┐   │               │
│         ├──►│   View Attendance Records     │   │               │
│         │   └──────────────────────────────┘   │               │
│         │                                       │               │
│         │   ┌──────────────────────────────┐   │               │
│         ├──►│   Download Report            │   │               │
│         │   └──────────────────────────────┘   │               │
│         │                                       │               │
│         │                   ┌──────────────────────────────┐    │
│         │                   ├──►│   Create Class          │    │
│         │                   │   └──────────────────────────┘    │
│         │                   │                                    │
│         │                   │   ┌──────────────────────────┐    │
│         │                   ├──►│   Create Session        │    │
│         │                   │   └──────────────────────────┘    │
│         │                   │                                    │
│         │                   │   ┌──────────────────────────┐    │
│         │                   ├──►│   Enroll Students       │    │
│         │                   │   └──────────────────────────┘    │
│         │                   │                                    │
│         │                   │   ┌──────────────────────────┐    │
│         │                   ├──►│   Mark Attendance       │    │
│         │                   │   └──────────────────────────┘    │
│         │                   │                                    │
│         │                   │   ┌──────────────────────────┐    │
│         │                   ├──►│   Generate Report       │    │
│         │                   │   └──────────────────────────┘    │
│         │                   │                                    │
│         │                   ┌──────────────────────────────┐    │
│         │                   │   Manage System Settings     │    │
│         │                   ├──►│   Manage Users           │    │
│         │                   │   │   View All Reports       │    │
│         │                   │   │   System Configuration   │    │
│         │                   │   └──────────────────────────┘    │
│         │                                                        │
│  Include actors, dependencies, and extend relationships         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. UML Class Diagram (Key Classes)

```
┌────────────────────────────┐
│         User               │
├────────────────────────────┤
│ -id: int                   │
│ -email: str (unique)       │
│ -password: str (hashed)    │
│ -first_name: str           │
│ -role: Role                │
│ -is_active: bool           │
│ -login_attempts: int       │
├────────────────────────────┤
│ +get_full_name(): str      │
│ +is_account_locked(): bool │
│ +reset_login_attempts()    │
└────────────────────────────┘
         △        △
         │        │
    ┌────┘        └────┐
    │                  │
┌───┴──────────┐ ┌────┴───────────┐
│ Instructor   │ │    Student     │
├──────────────┤ ├────────────────┤
│             │ │                │
│ inherits    │ │ inherits       │
│ from User   │ │ from User      │
└──────────────┘ └────────────────┘
    △ 1                △ N
    │ teaches          │ attends
    │ N:1              │ N:M
    │                  │
┌───┴──────────────────┴───────────┐
│          Class                    │
├───────────────────────────────────┤
│ -id: int                          │
│ -code: str (unique)               │
│ -name: str                        │
│ -instructor: User                 │
│ -capacity: int                    │
│ -start_date: date                 │
│ -end_date: date                   │
│ -is_active: bool                  │
├───────────────────────────────────┤
│ +get_enrolled_count(): int        │
│ +get_available_slots(): int       │
│ +is_ongoing(): bool               │
└───────────────────────────────────┘
    △ 1
    │ contains
    │ 1:N
    │
    └──────┐
           │
        ┌──┴──────────────┐
        │     Session     │
        ├─────────────────┤
        │ -id: int        │
        │ -class: Class   │
        │ -date: date     │
        │ -start_time: time
        │ -end_time: time │
        │ -topic: str     │
        │ -is_held: bool  │
        ├─────────────────┤
        │ +get_duration() │
        └──────┬──────────┘
               │ 1
               │ has
               │ 1:N
               │
               ▼
        ┌─────────────────────────┐
        │  AttendanceRecord       │
        ├─────────────────────────┤
        │ -id: int                │
        │ -student: Student       │
        │ -session: Session       │
        │ -status: str            │
        │ -check_in_time: datetime
        │ -check_out_time: datetime
        │ -marked_by: User        │
        ├─────────────────────────┤
        │ +get_duration(): int    │
        │ +is_late(): bool        │
        └─────────────────────────┘
```

---

## 5. UML Sequence Diagram - Attendance Marking

```
Student    Instructor        API         Database
  │            │              │             │
  │            │              │             │
  │         [1] Login─────────►│             │
  │            │              │             │
  │            │         [2] Validate──────►│
  │            │              │             │
  │            │◄─────────[3] JWT Token─────│
  │            │              │             │
  │            │ [4] Request Mark Attendance
  │            │──────────────►│             │
  │            │              │             │
  │            │         [5] Check Permission
  │            │         & Validate Data
  │            │              │             │
  │            │         [6] Create Record─►│
  │            │              │             │
  │            │◄─────────[7] Success──────│
  │            │              │             │
  │         [8] View Records──►│             │
  │            │              │             │
  │            │         [9] Query Records──►
  │            │              │             │
  │            │◄─────────[10] Return Data──│
  │            │              │             │
  │◄───────[11] Display Results─────────────│
  │            │              │             │
```

---

## 6. System State Diagram

```
┌─────────────┐
│   Not       │
│  Logged In  │
│             │
└──────┬──────┘
       │ login()
       ▼
┌─────────────────┐
│  Logged In      │
│  (Authenticated)│
└──┬──────────┬───┘
   │ teacher  │ student
   │          │
   ▼          ▼
┌──────────┐  ┌─────────┐
│ Instructor│ │ Student │
│  State   │  │  State  │
└──────────┘  └─────────┘
   │              │
   │ Create Class │ View Classes
   │              │
   ├──────┬───────┤
   │      │       │
   │      ▼       │
   │  ┌──────────────┐
   │  │ View Records │
   │  └──────────────┘
   │      ▲
   │      │ Mark Attendance
   │      │
   └──────┴─────────────────┐
          │                 │
          │ logout()        │
          │                 │
          ▼                 ▼
       ┌──────────────────────┐
       │  Logged Out / Exit   │
       └──────────────────────┘
```

---

## 7. Component Diagram

```
┌────────────────────────────────────────────────────────────┐
│              Presentation Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Django       │  │ Bootstrap    │  │ JavaScript   │   │
│  │ Templates    │  │ CSS Framework│  │ (Fetch API)  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              Application Layer (DRF)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ ViewSets     │  │ Serializers  │  │ Permissions  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              Business Logic Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Report       │  │ Attendance   │  │ Auth         │   │
│  │ Services     │  │ Services     │  │ Services     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              Data Layer (ORM)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Models       │  │ QuerySets    │  │ Migrations   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              Database Layer                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              MySQL Database                          │ │
│  │  (Users, Roles, Classes, Sessions, Attendance, etc) │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

---

## 8. Deployment Architecture

```
                        ┌──────────────┐
                        │  Clients     │
                        │ (Web Browsers)
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │    Nginx     │
                        │  (Reverse    │
                        │   Proxy)     │
                        └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
            ┌──────────────┐      ┌──────────────┐
            │  Gunicorn    │      │   Daphne     │
            │  (WSGI App)  │      │  (ASGI App)  │
            │ Workers: N   │      │  Workers: M  │
            └──────┬───────┘      └──────┬───────┘
                    │                     │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
            ┌──────────────┐      ┌──────────────┐
            │ MySQL        │      │   Redis      │
            │ Database     │      │ Cache/Queue  │
            │              │      │              │
            └──────────────┘      └──────┬───────┘
                                         │
                                  ┌──────┴──────┐
                                  │             │
                                  ▼             ▼
                          ┌─────────────┐   ┌─────────────┐
                          │ Celery      │   │ Celery Beat │
                          │ Workers     │   │ (Scheduler) │
                          └─────────────┘   └─────────────┘
```

---

**Generated**: January 3, 2026
