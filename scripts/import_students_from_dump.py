"""Quick importer to create student user accounts from Dump20260102.sql.

Only minimal fields are kept for attendance:
- username: student_number when available, otherwise email prefix
- first_name / last_name
- email
- phone_number
- role: student (if defined)

Organization/program/section fields from the dump are intentionally ignored.
Run with the project virtualenv active and MySQL env vars set if needed:
    python scripts/import_students_from_dump.py
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import django
from django.db import transaction

BASE_DIR = Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "Dump20260102.sql"
INSERT_MARKER = "INSERT INTO `member` VALUES "


def _parse_member_rows(sql_text: str) -> list[tuple]:
    """Extract tuple rows from the member insert in the dump."""
    start = sql_text.find(INSERT_MARKER)
    if start == -1:
        raise RuntimeError("Could not find member insert statement in dump")
    start += len(INSERT_MARKER)
    end = sql_text.find(";", start)
    if end == -1:
        raise RuntimeError("Could not find end of member insert statement")
    payload = sql_text[start:end].strip()
    # Wrap as a Python list of tuples for ast.literal_eval
    return ast.literal_eval(f"[{payload}]")


def _safe_username(student_number: str | None, email: str) -> str:
    """Build a unique username from student_number or email prefix."""
    from apps.users.models import User  # local import to keep django.setup first

    base = (student_number or email.split("@", 1)[0] or "student").strip()
    base = base.replace(" ", "").replace("/", "").replace("\\", "")[:150]
    if not base:
        base = "student"

    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}-{suffix}"[:150]
        suffix += 1
    return candidate


@transaction.atomic
def import_students(rows: list[tuple]) -> tuple[int, int]:
    """Create student users; returns (created, skipped_existing)."""
    from apps.users.models import Role, User

    student_role = Role.objects.filter(name=Role.RoleChoices.STUDENT).first()

    created = 0
    skipped = 0
    for row in rows:
        (
            _id,
            first_name,
            middle_name,
            last_name,
            _birthday,
            _is_working,
            _address,
            email,
            phone_number,
            student_number,
            *_rest,
        ) = row

        email = (email or "").strip()
        if not email:
            skipped += 1
            continue

        username = _safe_username(student_number, email)
        defaults = {
            "username": username,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "phone_number": phone_number or "",
            "role": student_role,
            "is_active": True,
        }

        user, was_created = User.objects.get_or_create(email=email, defaults=defaults)
        if was_created:
            user.set_password("ChangeMe123!")
            user.save(update_fields=["password"])
            created += 1
        else:
            skipped += 1

    return created, skipped


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    if not DUMP_PATH.exists():
        raise FileNotFoundError(f"Dump file not found: {DUMP_PATH}")

    sql_text = DUMP_PATH.read_text(encoding="utf-8")
    rows = _parse_member_rows(sql_text)
    created, skipped = import_students(rows)
    print(f"Students created: {created}")
    print(f"Skipped (existing or missing email): {skipped}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - convenience for ad-hoc run
        print(f"Import failed: {exc}", file=sys.stderr)
        sys.exit(1)
