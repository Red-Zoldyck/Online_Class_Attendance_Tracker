import csv
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.classes.models import Course, Program, Section, SectionCourse, Term, YearLevel

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
    help = (
        "Import course catalog CSV, ensure sections per year, and create SectionCourse records "
        "for a target term."
    )

    def add_arguments(self, parser):
        parser.add_argument("--csv", dest="csv_path", required=True, help="Path to CSV file")
        parser.add_argument("--program", dest="program_code", required=True, help="Program code, e.g., BSCS")
        parser.add_argument(
            "--school-year",
            dest="school_year",
            required=True,
            help="School year for the target term, e.g., 2025-2026",
        )
        parser.add_argument(
            "--term",
            dest="term",
            required=True,
            choices=["1", "2"],
            help="Term/semester code: 1 or 2",
        )
        parser.add_argument(
            "--section-codes",
            dest="section_codes",
            default="1A,2A,3A,4A",
            help="Comma-separated section codes per year (1-4). Example: '1A,2A,3A,4A'",
        )
        parser.add_argument(
            "--sections-only",
            action="store_true",
            help="Only create sections (and year levels) from CSV; skip course and section-course creation",
        )
        parser.add_argument("--dry-run", action="store_true", help="Parse and report without saving changes")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        program_code = options["program_code"]
        school_year = options["school_year"]
        term_code = options["term"]
        section_code_list = [c.strip() for c in options["section_codes"].split(",") if c.strip()]
        sections_only = options["sections_only"]
        dry_run = options["dry_run"]

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        try:
            program = Program.objects.get(code=program_code)
        except Program.DoesNotExist:
            raise CommandError(f"Program not found: {program_code}")

        rows = self._read_csv(csv_path)
        if not rows:
            raise CommandError("CSV has no data rows")

        summary = self._import(rows, program, school_year, term_code, section_code_list, sections_only, dry_run)
        self.stdout.write(self.style.SUCCESS(summary))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run mode: no database changes saved."))

    @transaction.atomic
    def _import(
        self,
        rows: List[Dict[str, str]],
        program: Program,
        school_year: str,
        term_code: str,
        section_code_list: List[str],
        sections_only: bool,
        dry_run: bool,
    ) -> str:
        created_courses = 0
        updated_courses = 0
        created_sections = 0
        created_sc = 0
        skipped = 0
        errors: List[str] = []
        warnings: List[str] = []

        # Term: only needed when creating section-courses
        term_obj = None
        if not sections_only:
            term_obj = (
                Term.objects.filter(program=program, school_year=school_year, term=term_code, year_level__isnull=True)
                .order_by("id")
                .first()
            )
            if not term_obj and not dry_run:
                term_obj = Term.objects.create(program=program, school_year=school_year, term=term_code, year_level=None)

        for idx, row in enumerate(rows, start=1):
            code = row.get("code", "").strip()
            title = row.get("subject", "").strip()
            prereq = row.get("prerequisite", "").strip()
            units_raw = row.get("units", "").strip()
            section_code_raw = row.get("section", "").strip()
            year_raw = row.get("year", "").strip().upper()
            term_raw = row.get("term", "").strip().upper()

            if not code or not title:
                skipped += 1
                continue

            year_num = YEAR_MAP.get(year_raw)
            suggested_term = TERM_MAP.get(term_raw)
            if not year_num:
                errors.append(f"Row {idx}: unknown year '{year_raw}' for {code}")
                skipped += 1
                continue

            try:
                units = Decimal(units_raw) if units_raw else None
            except Exception:
                errors.append(f"Row {idx}: invalid units '{units_raw}' for {code}")
                skipped += 1
                continue

            defaults = {
                "title": title,
                "units": units if units is not None else Decimal("0"),
                "suggested_year": year_num,
                "suggested_term": suggested_term,
                "description": f"Prerequisite: {prereq}" if prereq else "",
            }

            if not sections_only:
                if dry_run:
                    # Skip DB writes in dry-run
                    pass
                else:
                    course, created_flag = Course.objects.update_or_create(
                        program=program,
                        code=code,
                        defaults=defaults,
                    )
                    if created_flag:
                        created_courses += 1
                    else:
                        updated_courses += 1

            # Ensure YearLevel and Section
            year_level, _ = YearLevel.objects.get_or_create(program=program, number=year_num)

            # Prefer explicit section code from CSV; otherwise fallback per-year list
            if section_code_raw:
                inferred_program_code = section_code_raw.split()[0] if " " in section_code_raw else None
                if inferred_program_code and inferred_program_code != program.code:
                    warnings.append(
                        f"Row {idx}: section '{section_code_raw}' program '{inferred_program_code}' does not match target program '{program.code}'; skipped section assignment"
                    )
                    skipped += 1
                    continue
                section_code = section_code_raw
            else:
                section_code = section_code_list[year_num - 1] if len(section_code_list) >= year_num else f"{year_num}A"

            section_exists = Section.objects.filter(program=program, year_level=year_level, code=section_code).exists()
            if dry_run:
                if not section_exists:
                    created_sections += 1
            else:
                section, sec_created = Section.objects.get_or_create(
                    program=program,
                    year_level=year_level,
                    code=section_code,
                    defaults={"capacity": 50, "is_active": True},
                )
                if sec_created:
                    created_sections += 1

                if not sections_only:
                    sc, sc_created = SectionCourse.objects.get_or_create(
                        section=section,
                        course=course,
                        term=term_obj,
                        defaults={"capacity": section.capacity, "is_active": True},
                    )
                    if sc_created:
                        created_sc += 1

        summary = (
            f"Processed {len(rows)} rows; created_courses={created_courses}, updated_courses={updated_courses}, "
            f"created_sections={created_sections}, created_section_courses={created_sc}, skipped={skipped}, errors={len(errors)}"
        )
        if errors:
            for err in errors:
                self.stdout.write(self.style.WARNING(err))
        if warnings:
            for warn in warnings:
                self.stdout.write(self.style.WARNING(warn))
        return summary

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows: List[Dict[str, str]] = []
            for row in reader:
                norm = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
                rows.append(norm)
            return rows
