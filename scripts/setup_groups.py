"""
Seed sensible Django auth groups with permissions.

Groups created:
- Admins: all permissions
- Instructors: attendance add/change/view, class/session view
- Students: class/session view
"""

import os
import sys
from pathlib import Path


def bootstrap_env():
    base_dir = Path(__file__).resolve().parent.parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    os.environ["DB_ENGINE"] = "django.db.backends.mysql"
    os.environ["DB_NAME"] = "attendance_tracker"
    os.environ["DB_USER"] = "root"
    os.environ["DB_PASSWORD"] = "@dmin123"
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PORT"] = "3306"
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"


def main():
    bootstrap_env()
    import django

    django.setup()

    from django.conf import settings
    engine = settings.DATABASES['default']['ENGINE']
    name = settings.DATABASES['default']['NAME']
    print(f"Using DB engine={engine}, name={name}")

    from django.contrib.auth.models import Group, Permission

    def set_group(name, perm_qs):
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set(list(perm_qs))
        group.save()
        print(f"{name}: {group.permissions.count()} perms")

    set_group("Admins", Permission.objects.all())

    instructor_codes = [
        "add_attendancerecord",
        "change_attendancerecord",
        "view_attendancerecord",
        "view_class",
        "view_session",
    ]
    set_group(
        "Instructors",
        Permission.objects.filter(codename__in=instructor_codes),
    )

    student_codes = [
        "view_class",
        "view_session",
    ]
    set_group("Students", Permission.objects.filter(codename__in=student_codes))


if __name__ == "__main__":
    main()