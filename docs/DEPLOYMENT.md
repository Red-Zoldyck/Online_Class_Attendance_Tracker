# Deployment Guide - Online Class Attendance Tracker

## Production Features Summary

Before deployment, ensure you understand the following production features:

- **Real-time Digital Clock**: Displays on attendance marking pages in 12-hour format with date
- **Attendance Schedule Enforcement**: 6 AM window → 4-hour per-student lock → 8-hour report deadline
- **Web Reports Dashboard**: Generate and print attendance reports filtered by class and date
- **CSV Student Import**: Case-insensitive import with flexible name parsing and title-casing
- **Admin Management Portal**: Dashboard for managing academics, approving instructors, syncing enrollments
- **Role-Based Access Control**: Admin, Instructor, and Student roles with specific permissions
- **Attendance Status Codes**: P (Present), A (Absent), L (Late), E (Excused)
- **Navigation Integration**: Reports link and unified menu across all pages

---

## Production Deployment Checklist

### 1. Environment Configuration

Before deploying, ensure all security settings are configured:

```bash
# Copy environment template
cp .env.example .env

# Configure production settings
DEBUG=False
SECRET_KEY=<generate-secure-random-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_ENGINE=django.db.backends.mysql
DB_NAME=attendance_tracker_prod
DB_USER=<database-user>
DB_PASSWORD=<strong-database-password>
DB_HOST=<database-server-ip>
DB_PORT=3306
```

### 2. Security Hardening

#### Django Settings (config/settings.py)

```python
# Production settings
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
```

#### Database Security

1. Use strong database passwords
2. Restrict database access to application server only
3. Enable MySQL SSL connections
4. Regular database backups (daily minimum)

### 3. Server Setup

#### Web Server (Nginx + Gunicorn)

**Install Gunicorn**:
```bash
pip install gunicorn
```

**Gunicorn Configuration** (`gunicorn_config.py`):
```python
import multiprocessing

bind = "127.0.0.1:8001"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

**Run Gunicorn**:
```bash
gunicorn -c gunicorn_config.py config.wsgi:application
```

#### Nginx Configuration

Create `/etc/nginx/sites-available/attendance_tracker`:

```nginx
upstream attendance_tracker {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 100M;

    location / {
        proxy_pass http://attendance_tracker;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /var/www/attendance_tracker/staticfiles/;
    }

    location /media/ {
        alias /var/www/attendance_tracker/media/;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/attendance_tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Database Setup

#### MySQL Configuration

1. **Create Database and User**:
```sql
CREATE DATABASE attendance_tracker_prod 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'attendance_user'@'localhost' 
    IDENTIFIED BY 'strong_password_here';

GRANT ALL PRIVILEGES ON attendance_tracker_prod.* 
    TO 'attendance_user'@'localhost';

FLUSH PRIVILEGES;
```

2. **Run Migrations**:
```bash
python manage.py migrate --settings=config.settings
```

3. **Create Initial Data**:
```bash
python manage.py shell --settings=config.settings
from apps.users.models import Role
Role.objects.create(name='admin', display_name='Administrator')
Role.objects.create(name='instructor', display_name='Instructor')
Role.objects.create(name='student', display_name='Student')
exit()
```

**Admin Account Registration**: When deploying to production, users can register as administrators using the code: `@dm|n@2o2G!`

This code is validated in the user registration API endpoint. Admins can then access the admin dashboard to manage system settings, approve instructor applications, and manage student enrollments.

4. **Create Superuser**:
```bash
python manage.py createsuperuser --settings=config.settings
```

### 5. Systemd Service Files

#### Gunicorn Service (`/etc/systemd/system/attendance_tracker.service`)

```ini
[Unit]
Description=Attendance Tracker Gunicorn Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/attendance_tracker
Environment="PATH=/var/www/attendance_tracker/venv/bin"
ExecStart=/var/www/attendance_tracker/venv/bin/gunicorn \
    -c gunicorn_config.py \
    config.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable attendance_tracker
sudo systemctl start attendance_tracker
```

#### Celery Service (`/etc/systemd/system/attendance_tracker_celery.service`)

```ini
[Unit]
Description=Attendance Tracker Celery
After=network.target attendance_tracker.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/attendance_tracker
Environment="PATH=/var/www/attendance_tracker/venv/bin"
ExecStart=/var/www/attendance_tracker/venv/bin/celery -A config worker \
    -l info --logfile=/var/log/celery_worker.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6. SSL/TLS Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

### 7. Logging and Monitoring

#### Log Rotation (`/etc/logrotate.d/attendance_tracker`)

```
/var/www/attendance_tracker/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload attendance_tracker > /dev/null 2>&1 || true
    endscript
}
```

#### Monitoring

1. **Check Application Status**:
```bash
sudo systemctl status attendance_tracker
sudo journalctl -u attendance_tracker -f
```

2. **Check Nginx Status**:
```bash
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

3. **Database Monitoring**:
```bash
mysql -u attendance_user -p
SHOW PROCESSLIST;
SHOW STATUS LIKE 'Threads%';
```

### 8. Backup Strategy

#### Database Backup Script (`/usr/local/bin/backup_attendance.sh`)

```bash
#!/bin/bash

BACKUP_DIR="/backups/attendance_tracker"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="attendance_tracker_prod"
DB_USER="attendance_user"
DB_PASS="${DB_PASSWORD}"

mkdir -p $BACKUP_DIR

# Backup database
mysqldump -u $DB_USER -p$DB_PASS $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /var/www/attendance_tracker/media/

# Keep only last 30 days of backups
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

Schedule with Cron:
```bash
0 2 * * * /usr/local/bin/backup_attendance.sh >> /var/log/attendance_backup.log 2>&1
```

### 9. Health Checks

Create a health check endpoint in `apps/users/views.py`:

```python
from django.http import JsonResponse
from django.views import View

class HealthCheckView(View):
    def get(self, request):
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_ok = True
        except:
            db_ok = False
        
        return JsonResponse({
            'status': 'healthy' if db_ok else 'unhealthy',
            'database': db_ok
        })
```

### 10. Performance Tuning

#### Django Settings

```python
# Connection pooling
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 600,
    }
}

# Query optimization
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# Cache optimization
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}
```

#### MySQL Configuration (`/etc/mysql/mysql.conf.d/mysqld.cnf`)

```ini
[mysqld]
max_connections = 500
max_allowed_packet = 256M
innodb_buffer_pool_size = 4G
innodb_log_file_size = 1G
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
```

### 11. Deployment Checklist

Before going live:

- [ ] Environment variables configured
- [ ] SSL certificate installed
- [ ] Database migrated and tested
- [ ] Static files collected
- [ ] Superuser created
- [ ] Email service configured
- [ ] Backup strategy implemented
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] Security headers verified
- [ ] Rate limiting configured
- [ ] Database connections optimized
- [ ] All tests passing
- [ ] Load testing completed
- [ ] Documentation updated

---

## Local Development vs Production

| Setting | Development | Production |
|---------|-------------|-----------|
| DEBUG | True | False |
| SECRET_KEY | (any value) | Secure random string |
| ALLOWED_HOSTS | localhost | yourdomain.com |
| Database | SQLite | MySQL |
| Cache | Dummy | Redis |
| SSL Redirect | False | True |
| HSTS | 0 | 31536000 |

---

## Troubleshooting Deployment

### 502 Bad Gateway

Check Gunicorn:
```bash
sudo systemctl restart attendance_tracker
sudo journalctl -u attendance_tracker -n 50
```

### Database Connection Issues

```bash
mysql -u attendance_user -p -h localhost attendance_tracker_prod
```

### Static Files Not Loading

```bash
python manage.py collectstatic --noinput --clear
```

### Permission Issues

```bash
sudo chown -R www-data:www-data /var/www/attendance_tracker
sudo chmod -R 755 /var/www/attendance_tracker
```

---

**Last Updated**: January 3, 2026
