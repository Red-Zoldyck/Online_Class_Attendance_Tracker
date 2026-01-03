"""
Schedule importer for bulk CSV upload.
Parses schedule CSV files and updates SectionCourse with instructor assignments.
"""

import csv
import io
import re
from typing import Tuple, List, Dict, Set
from django.db import transaction
from apps.classes.models import SectionCourse, Course, Section, Term, Program, YearLevel
from apps.users.models import User, Role


TERM_MAP = {
    '1': '1',
    '01': '1',
    'FIRST SEM': '1',
    '1ST SEM': '1',
    'FIRST': '1',
    '1ST': '1',
    '2': '2',
    '02': '2',
    'SECOND SEM': '2',
    '2ND SEM': '2',
    'SECOND': '2',
    '2ND': '2',
}

YEAR_MAP = {
    'FIRST YEAR': 1,
    '1ST YEAR': 1,
    'YEAR 1': 1,
    '1': 1,
    'SECOND YEAR': 2,
    '2ND YEAR': 2,
    'YEAR 2': 2,
    '2': 2,
    'THIRD YEAR': 3,
    '3RD YEAR': 3,
    'YEAR 3': 3,
    '3': 3,
    'FOURTH YEAR': 4,
    '4TH YEAR': 4,
    'YEAR 4': 4,
    '4': 4,
}


def parse_schedule_csv(csv_file) -> Tuple[List[Dict], List[str]]:
    """
    Parse CSV file and extract schedule data.
    Returns (parsed_data, errors).
    """
    parsed_data = []
    errors = []
    missing_code_section_rows: List[int] = []
    missing_term_rows: List[int] = []
    missing_year_rows: List[int] = []
    
    try:
        # Decode file if it's bytes
        if isinstance(csv_file, bytes):
            content = csv_file.decode('utf-8')
        else:
            content = csv_file.read().decode('utf-8')

        csv_reader = csv.DictReader(io.StringIO(content))

        if not csv_reader.fieldnames:
            return [], ["Invalid CSV file: No headers found"]

        # Normalize header names once for flexible mapping
        normalized_headers = {h.lower().strip(): h for h in csv_reader.fieldnames if h}

        for row_num, row in enumerate(csv_reader, start=2):  # start=2 because header is row 1
            # Pull columns with fallbacks (support multiple header spellings)
            code = (
                row.get('CODE')
                or row.get('Course Code')
                or row.get('course_code')
                or row.get('course code')
                or ''
            ).strip()

            section_val = (
                row.get('section')
                or row.get('SECTION')
                or row.get('Section')
                or ''
            ).strip()

            description = (
                row.get('DESCRIPTION')
                or row.get('Course Name')
                or row.get('course_name')
                or row.get('TITLE')
                or row.get('Title')
                or row.get('title')
                or row.get('Course Title')
                or ''
            ).strip()

            instructor_name = (
                row.get('Name')
                or row.get('Full name with initials')
                or row.get('Instructor')
                or ''
            ).strip()

            # Build schedule; prefer explicit schedule field, else combine DAYS + TIME + ROOM
            schedule = (
                row.get('schedule')
                or row.get('SCHEDULE')
                or row.get('Schedule')
                or ''
            ).strip()

            if not schedule:
                days_val = (row.get('DAYS') or row.get('Days') or '').strip()
                time_val = (row.get('TIME') or row.get('Time') or '').strip()
                room_val = (row.get('ROOM') or row.get('Room') or '').strip()
                parts = [p for p in [days_val, time_val, room_val] if p]
                if parts:
                    schedule = ' | '.join(parts)

            term_raw = (
                row.get('TERM')
                or row.get('Term')
                or row.get('Semester')
                or row.get('SEMESTER')
                or ''
            ).strip()

            year_raw = (
                row.get('YEAR')
                or row.get('Year')
                or row.get('YEAR LEVEL')
                or row.get('Year Level')
                or ''
            ).strip()

            # If no explicit year column, attempt to derive from section code (e.g., "BSCS 1A" -> 1)
            if not year_raw and section_val:
                match = re.search(r'(\d)', section_val)
                if match:
                    year_raw = match.group(1)

            # If still missing, try derive from course code digits (e.g., CS 311 -> 3, GE 101 -> 1)
            if not year_raw and code:
                course_digit = re.search(r'([1-4])', code)
                if course_digit:
                    year_raw = course_digit.group(1)

            load_count_raw = row.get('Load Count', '') or row.get('load_count', '') or '0'

            # Skip empty rows
            if not code and not section_val:
                continue

            try:
                entry = {
                    'row_num': row_num,
                    'code': code,
                    'description': description,
                    'section': section_val,
                    'instructor_name': instructor_name,
                    'load_count': int(load_count_raw or 0),
                    'schedule': schedule,
                    'term_raw': term_raw,
                    'year_raw': year_raw,
                }

                if entry['code']:
                    if term_raw:
                        term_key = term_raw.upper().replace('.', '').replace('  ', ' ').strip()
                        term_code = TERM_MAP.get(term_key)
                        if not term_code:
                            missing_term_rows.append(row_num)
                        else:
                            entry['term_code'] = term_code
                            if year_raw:
                                year_key = year_raw.upper().replace('.', '').replace('  ', ' ').strip()
                                year_num = YEAR_MAP.get(year_key)
                                if not year_num:
                                    missing_year_rows.append(row_num)
                                else:
                                    entry['year_num'] = year_num
                                    parsed_data.append(entry)
                            else:
                                missing_year_rows.append(row_num)
                    else:
                        missing_term_rows.append(row_num)
                else:
                    missing_code_section_rows.append(row_num)
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        if missing_code_section_rows:
            shown = ', '.join(str(n) for n in missing_code_section_rows[:5])
            extra = '' if len(missing_code_section_rows) <= 5 else f" ... +{len(missing_code_section_rows) - 5} more"
            errors.append(
                f"Rows {shown}{extra}: Missing required 'code' or 'section'; skipped ({len(missing_code_section_rows)} total)."
            )
        if missing_term_rows:
            shown = ', '.join(str(n) for n in missing_term_rows[:5])
            extra = '' if len(missing_term_rows) <= 5 else f" ... +{len(missing_term_rows) - 5} more"
            errors.append(
                f"Rows {shown}{extra}: Missing or invalid TERM/SEM value; skipped ({len(missing_term_rows)} total)."
            )
        if missing_year_rows:
            shown = ', '.join(str(n) for n in missing_year_rows[:5])
            extra = '' if len(missing_year_rows) <= 5 else f" ... +{len(missing_year_rows) - 5} more"
            errors.append(
                f"Rows {shown}{extra}: Missing or invalid YEAR value; skipped ({len(missing_year_rows)} total)."
            )

        return parsed_data, errors

    except Exception as e:
        return [], [f"Failed to parse CSV: {str(e)}"]


@transaction.atomic
def import_schedule_data(parsed_data: List[Dict], program: Program, school_year: str, mode: str = 'all', skip_rows: Set[int] | None = None) -> Dict:
    """
    Import parsed schedule data into the database using per-row term from CSV.
    Matches courses to sections and assigns instructors.
    Auto-creates courses if they don't exist.
    Returns dict with import results.
    """
    results = {
        'success': 0,
        'skipped': 0,
        'errors': [],
        'warnings': [],
        'courses_created': 0
    }
    
    skip_rows = skip_rows or set()

    # Get or create instructor role
    instructor_role, _ = Role.objects.get_or_create(
        name='instructor',
        defaults={'display_name': 'Instructor'}
    )

    seen_courses = set()
    seen_sections = set()
    default_sections = {
        1: f"{program.code} 1A",
        2: f"{program.code} 2A",
        3: f"{program.code} 3A",
        4: f"{program.code} 4A",
    }
    
    for entry in parsed_data:
        if entry.get('row_num') in skip_rows:
            results['skipped'] += 1
            continue

        try:
            course_code = entry['code']
            section_code = entry.get('section')
            instructor_name = entry['instructor_name']
            course_description = entry['description']
            entry_schedule = entry.get('schedule', '')
            term_code = entry.get('term_code')
            year_num = entry.get('year_num')

            if not term_code:
                results['warnings'].append(
                    f"Row {entry['row_num']}: Missing term; skipped."
                )
                results['skipped'] += 1
                continue
            
            # Find or create course
            course = None
            section = None

            # Courses-only or modes that need courses
            if mode in {'all', 'schedule_only', 'courses_only', 'sections_only', 'courses_sections_exact_instructor'}:
                course_defaults = {
                    'title': course_description or course_code,
                    'suggested_year': year_num,
                    'suggested_term': term_code,
                    'description': course_description or ''
                }
                course, course_created = Course.objects.get_or_create(
                    code=course_code,
                    program=program,
                    defaults=course_defaults
                )
                if course_created:
                    results['courses_created'] += 1
                else:
                    updates = {}
                    if course_description and (not course.title or course.title.strip() == course_code):
                        updates['title'] = course_description
                    if course_description and not course.description:
                        updates['description'] = course_description
                    if updates:
                        for k, v in updates.items():
                            setattr(course, k, v)
                        course.save(update_fields=list(updates.keys()))
                if mode == 'courses_only':
                    if course_code not in seen_courses:
                        results['success'] += 1
                        seen_courses.add(course_code)
                    continue

            # Sections-only or modes that need sections
            # Find or create section
            if not year_num:
                results['warnings'].append(
                    f"Row {entry['row_num']}: Missing year; skipped."
                )
                results['skipped'] += 1
                continue

            section_blank = not section_code or section_code.upper() in {'N/A', 'NA', 'NONE'}
            if section_blank:
                section_code = default_sections.get(year_num)
            if not section_code:
                results['warnings'].append(
                    f"Row {entry['row_num']}: Missing section and no default for year {year_num}; skipped."
                )
                results['skipped'] += 1
                continue
            section = None
            try:
                # Exact match first within program
                section = Section.objects.get(code=section_code, program=program)
            except Section.DoesNotExist:
                # Try partial match (e.g., "BSCS 1A" might be stored as "1A" or similar)
                matching_sections = Section.objects.filter(code__icontains=section_code.split()[-1], program=program)
                if matching_sections.exists():
                    section = matching_sections.first()
                else:
                    # Try to auto-create section by parsing the code
                    # Expected format: "PROGRAM YEAR[LETTER]" (e.g., "BSCS 1A", "ACT 2B")
                    section_parts = section_code.split()
                    if len(section_parts) >= 2:
                        program_code = section_parts[0]
                        year_part = section_parts[1]  # e.g., "1A"
                        
                        # Extract year number from start of year_part
                        year_number = ''
                        for char in year_part:
                            if char.isdigit():
                                year_number += char
                            else:
                                break
                        
                        if year_number:
                            year_num = int(year_number)
                            # Try to find program and year level
                            try:
                                import_program = Program.objects.get(code=program_code)
                                year_level = YearLevel.objects.get(program=import_program, number=year_num)
                                
                                # Auto-create section
                                section, section_created = Section.objects.get_or_create(
                                    code=section_code,
                                    program=import_program,
                                    year_level=year_level,
                                    defaults={'capacity': 50, 'is_active': True}
                                )
                                
                                if section_created:
                                    results['courses_created'] += 1  # Track as created
                            except (Program.DoesNotExist, YearLevel.DoesNotExist):
                                results['warnings'].append(
                                    f"Cannot auto-create section {section_code}: Program or year level not found (Row {entry['row_num']})"
                                )
                                results['skipped'] += 1
                                continue
                    
                    if not section:
                        results['warnings'].append(
                            f"Section {section_code} not found for course {course_code} (Row {entry['row_num']})"
                        )
                        results['skipped'] += 1
                        continue
            
            if not section:
                results['warnings'].append(
                    f"Section {section_code} not found (Row {entry['row_num']})"
                )
                results['skipped'] += 1
                continue

            if section.program_id != program.id:
                results['warnings'].append(
                    f"Section {section.code} is under {section.program.code}, not {program.code}; skipped (Row {entry['row_num']})"
                )
                results['skipped'] += 1
                continue

            if not section.year_level:
                results['warnings'].append(
                    f"Section {section.code} has no year level; skipped (Row {entry['row_num']})"
                )
                results['skipped'] += 1
                continue

            # Backfill suggested_year/term on course once we know the section year
            if course and section and section.year_level:
                updates = {}
                if course.suggested_year is None:
                    updates['suggested_year'] = section.year_level.number
                if course.suggested_term is None:
                    updates['suggested_term'] = term_code
                if updates:
                    for k, v in updates.items():
                        setattr(course, k, v)
                    course.save(update_fields=list(updates.keys()))

            # If mode is sections_only, stop after creating/finding sections
            if mode == 'sections_only':
                section_key = f"{section.program_id}:{section.year_level_id}:{section.code}"
                if section_key not in seen_sections:
                    results['success'] += 1
                    seen_sections.add(section_key)
                continue
            
            # Resolve term per section/year level
            term = None
            try:
                term, _ = Term.objects.get_or_create(
                    program=program,
                    year_level=section.year_level,
                    term=term_code,
                    school_year=school_year,
                )
            except Exception as e:
                results['warnings'].append(
                    f"Row {entry['row_num']}: Failed to resolve term ({term_code} {school_year}) - {str(e)}"
                )
                results['skipped'] += 1
                continue

            # Find or create SectionCourse
            section_course, created = SectionCourse.objects.get_or_create(
                section=section,
                course=course,
                term=term,
                defaults={
                    'capacity': section.capacity,
                    'schedule': entry_schedule,
                    'is_active': True,
                }
            )

            # If schedule provided in CSV, update even when record already existed
            if entry_schedule:
                section_course.schedule = entry_schedule
                section_course.save(update_fields=['schedule'])
            
            # Find and assign instructor if provided and mode allows
            if instructor_name and mode in {'all', 'schedule_only', 'courses_sections_exact_instructor'}:
                instructor = None
                instructor_qs = User.objects.filter(role=instructor_role)

                if mode == 'courses_sections_exact_instructor':
                    # Exact match on first + last name (case-insensitive), no auto-create
                    name_clean = instructor_name.strip()
                    first_name = ''
                    last_name = ''
                    if ',' in name_clean:
                        parts = [p.strip() for p in name_clean.split(',') if p.strip()]
                        if parts:
                            last_name = parts[0]
                            first_name = parts[1] if len(parts) > 1 else ''
                    else:
                        parts = name_clean.split()
                        if len(parts) >= 2:
                            last_name = parts[-1]
                            first_name = ' '.join(parts[:-1])

                    if first_name and last_name:
                        instructor = instructor_qs.filter(
                            first_name__iexact=first_name,
                            last_name__iexact=last_name,
                        ).first()

                    if not instructor:
                        results['warnings'].append(
                            f"Instructor '{instructor_name}' not assigned (exact match required) for {course_code} {section_code} (Row {entry['row_num']})"
                        )
                else:
                    # Flexible search and auto-create (current behavior)
                    name_parts = instructor_name.replace(',', '').split()
                    if len(name_parts) >= 2:
                        last_name = name_parts[0]
                        first_name = name_parts[1] if len(name_parts) > 1 else ''
                        instructor = instructor_qs.filter(
                            last_name__icontains=last_name,
                            first_name__icontains=first_name
                        ).first()
                    if not instructor:
                        instructor = instructor_qs.filter(
                            first_name__icontains=instructor_name
                        ).first()
                    if not instructor:
                        try:
                            name_parts = instructor_name.replace(',', '').strip().split()
                            if len(name_parts) >= 2:
                                first_name = name_parts[0] if not instructor_name.startswith(name_parts[0] + ',') else (name_parts[1] if len(name_parts) > 1 else '')
                                last_name = name_parts[-1] if not instructor_name.startswith(name_parts[0] + ',') else name_parts[0]
                                if ',' in instructor_name:
                                    parts = [p.strip() for p in instructor_name.split(',')]
                                    last_name = parts[0]
                                    first_name = parts[1] if len(parts) > 1 else ''
                                email = f"{first_name.lower()}.{last_name.lower()}@school.edu"
                                from django.contrib.auth import get_user_model
                                User_model = get_user_model()
                                instructor, created_user = User_model.objects.get_or_create(
                                    email=email,
                                    defaults={
                                        'username': email.split('@')[0],
                                        'first_name': first_name[:30],
                                        'last_name': last_name[:30],
                                        'role': instructor_role,
                                        'is_active': True
                                    }
                                )
                                if created_user:
                                    instructor.set_password('DefaultPassword123!')
                                    instructor.save()
                                    results['warnings'].append(
                                        f"Auto-created instructor account for '{instructor_name}' (email: {email})"
                                    )
                        except Exception as e:
                            results['warnings'].append(
                                f"Could not auto-create instructor '{instructor_name}': {str(e)}"
                            )

                if instructor:
                    section_course.instructor = instructor
                    section_course.save(update_fields=['instructor'])
                else:
                    if mode == 'all':
                        results['warnings'].append(
                            f"Instructor '{instructor_name}' not found and could not be created for {course_code} {section_code} (Row {entry['row_num']})"
                        )
            
            results['success'] += 1
        
        except Exception as e:
            results['errors'].append(
                f"Row {entry['row_num']}: Failed to import - {str(e)}"
            )
    
    return results
