import csv
from decimal import Decimal
from pathlib import Path
from typing import Dict, Tuple

from django.core.management.base import BaseCommand, CommandError

from apps.classes.models import Course, Program


YEAR_MAP: Dict[str, int] = {
    "FIRST YEAR": 1,
    "SECOND YEAR": 2,
    "THIRD YEAR": 3,
    "FOURTH YEAR": 4,
}

TERM_MAP: Dict[str, str] = {
    "FIRST SEM": "1",
    "SECOND SEM": "2",
}


class Command(BaseCommand):
    help = "Import course catalog CSV into a program (code, subject, year, term, prerequisite, units)."

    def add_arguments(self, parser):
        parser.add_argument("--csv", dest="csv_path", required=True, help="Path to CSV file")
        parser.add_argument("--program", dest="program_code", required=True, help="Program code, e.g., BSCS")
        parser.add_argument("--dry-run", action="store_true", help="Parse and report without saving changes")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        program_code = options["program_code"]
        dry_run = options["dry_run"]

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        try:
            program = Program.objects.get(code=program_code)
        except Program.DoesNotExist:
            raise CommandError(f"Program not found: {program_code}")

        rows = self._read_csv(csv_path)
        created = 0
        updated = 0
        skipped = 0
        errors = []

        for idx, row in enumerate(rows, start=1):
            code = row.get("code", "").strip()
            title = row.get("subject", "").strip()
            prereq = row.get("prerequisite", "").strip()
            units_raw = row.get("units", "").strip()
            year_raw = row.get("year", "").strip().upper()
            term_raw = row.get("term", "").strip().upper()

            if not code or not title:
                skipped += 1
                continue

            suggested_year = YEAR_MAP.get(year_raw)
            suggested_term = TERM_MAP.get(term_raw)

            try:
                units = Decimal(units_raw) if units_raw else None
            except Exception:
                errors.append(f"Row {idx}: invalid units '{units_raw}' for {code}")
                skipped += 1
                continue

            defaults = {
                "title": title,
                "units": units if units is not None else Decimal("0"),
                "suggested_year": suggested_year,
                "suggested_term": suggested_term,
                "description": f"Prerequisite: {prereq}" if prereq else "",
            }

            if dry_run:
                continue

            course, created_flag = Course.objects.update_or_create(
                program=program,
                code=code,
                defaults=defaults,
            )

            if created_flag:
                created += 1
            else:
                updated += 1

        summary = (
            f"Processed {len(rows)} rows; "
            f"created={created}, updated={updated}, skipped={skipped}, errors={len(errors)}"
        )
        self.stdout.write(self.style.SUCCESS(summary))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run mode: no database changes saved."))
        for err in errors:
            self.stdout.write(self.style.WARNING(err))

    def _read_csv(self, path: Path):
        with path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # Normalize headers to lower snake_case keys
            normalized_rows = []
            for row in reader:
                normalized = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
                normalized_rows.append(normalized)
            return normalized_rows
