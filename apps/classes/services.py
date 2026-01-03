from typing import Tuple

from apps.classes.models import Course, Term, ClassSection, Section, SectionCourse


def sync_section_courses_for_course(course: Course) -> Tuple[int, int]:
    """
    Create SectionCourse entries for a course by combining with all matching Sections and Terms.
    Matches based on program, year_level, and term.
    Returns (created_count, skipped_count).
    """
    if not course.suggested_year or not course.suggested_term:
        return 0, 0

    # Find all matching sections (program + year_level)
    sections = Section.objects.filter(
        program=course.program,
        year_level__number=course.suggested_year,
        is_active=True
    )
    
    # Find all matching terms (program + year_level + term)
    terms = Term.objects.filter(
        program=course.program,
        year_level__number=course.suggested_year,
        term=course.suggested_term
    )
    
    if not sections.exists() or not terms.exists():
        return 0, 0

    created = 0
    skipped = 0

    for section in sections:
        for term in terms:
            section_course, was_created = SectionCourse.objects.get_or_create(
                section=section,
                course=course,
                term=term,
                defaults={
                    'capacity': section.capacity,
                    'schedule': '',
                    'is_active': True,
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    return created, skipped


def sync_sections_for_new_course(course: Course) -> Tuple[int, int]:
    """
    Create class sections for a newly added course based on existing section codes
    for the same program, year level, and term. Returns (created_count, skipped_count).
    """
    if not course.suggested_year or not course.suggested_term:
        return 0, 0

    terms = Term.objects.filter(
        program=course.program,
        term=course.suggested_term,
        year_level__number=course.suggested_year,
    )
    if not terms.exists():
        return 0, 0

    template_sections = (
        ClassSection.objects.filter(
            term__program=course.program,
            term__year_level__number=course.suggested_year,
            term__term=course.suggested_term,
        )
        .select_related('term')
        .order_by('created_at')
    )

    templates_by_code = {}
    for section in template_sections:
        # Keep the first seen per section code as the template
        templates_by_code.setdefault(section.section_code, section)

    # Fallback: if no existing ClassSection templates, use base Section rows for that program/year
    if not templates_by_code:
        base_sections = Section.objects.filter(
            program=course.program,
            year_level__number=course.suggested_year,
        ).order_by('code')
        for base in base_sections:
            templates_by_code[base.code] = base  # store Section; handle capacity in defaults below

    created = 0
    skipped = 0

    for term in terms:
        for code, template in templates_by_code.items():
            section, was_created = ClassSection.objects.get_or_create(
                course=course,
                term=term,
                section_code=code,
                defaults={
                    'capacity': getattr(template, 'capacity', 40),
                    'schedule': getattr(template, 'schedule', ''),
                    'is_active': getattr(template, 'is_active', True),
                    'platform_url': getattr(template, 'platform_url', ''),
                    'start_date': getattr(template, 'start_date', None),
                    'end_date': getattr(template, 'end_date', None),
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    return created, skipped


def sync_section_courses_for_term(term: Term) -> Tuple[int, int]:
    """
    Create SectionCourse entries for a new term by combining with all matching Sections and Courses.
    Returns (created_count, skipped_count).
    """
    # Find all matching sections (program + year_level)
    sections = Section.objects.filter(
        program=term.program,
        year_level=term.year_level,
        is_active=True
    )
    
    # Find all matching courses (program + suggested_year + suggested_term)
    courses = Course.objects.filter(
        program=term.program,
        suggested_year=term.year_level.number,
        suggested_term=term.term
    )
    
    if not sections.exists() or not courses.exists():
        return 0, 0

    created = 0
    skipped = 0

    for section in sections:
        for course in courses:
            section_course, was_created = SectionCourse.objects.get_or_create(
                section=section,
                course=course,
                term=term,
                defaults={
                    'capacity': section.capacity,
                    'schedule': '',
                    'is_active': True,
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    return created, skipped


def sync_section_courses_from_class_sections() -> Tuple[int, int]:
    """
    Backfill SectionCourse records from existing ClassSection rows.

    This is used for older data where ClassSection already exists but
    SectionCourse/Section rows were not created. It will:
    - Ensure a Section exists for the class section's program/year/code.
    - Create the SectionCourse for the (section, course, term) trio.
    - Carry over schedule/platform/capacity dates and instructor (latest assignment).
    Returns (created_count, skipped_count).
    """

    created = 0
    skipped = 0

    class_sections = (
        ClassSection.objects
        .select_related('course', 'term__program', 'term__year_level')
        .prefetch_related('teaching_assignments__instructor')
    )

    for class_section in class_sections:
        term = class_section.term
        course = class_section.course

        if not term or not term.year_level:
            skipped += 1
            continue

        if term.program_id != course.program_id:
            skipped += 1
            continue

        section_defaults = {
            'capacity': class_section.capacity,
            'is_active': class_section.is_active,
        }

        section, _ = Section.objects.get_or_create(
            program=term.program,
            year_level=term.year_level,
            code=class_section.section_code,
            defaults=section_defaults,
        )

        section_course_defaults = {
            'capacity': class_section.capacity,
            'schedule': class_section.schedule,
            'platform_url': class_section.platform_url,
            'is_active': class_section.is_active,
            'start_date': class_section.start_date,
            'end_date': class_section.end_date,
        }

        section_course, was_created = SectionCourse.objects.get_or_create(
            section=section,
            course=course,
            term=term,
            defaults=section_course_defaults,
        )

        if was_created:
            created += 1
        else:
            skipped += 1
            updates = {}

            if class_section.schedule and not section_course.schedule:
                updates['schedule'] = class_section.schedule
            if class_section.platform_url and not section_course.platform_url:
                updates['platform_url'] = class_section.platform_url
            if class_section.start_date and not section_course.start_date:
                updates['start_date'] = class_section.start_date
            if class_section.end_date and not section_course.end_date:
                updates['end_date'] = class_section.end_date
            if class_section.capacity and section_course.capacity < class_section.capacity:
                updates['capacity'] = class_section.capacity

            if updates:
                for field, value in updates.items():
                    setattr(section_course, field, value)
                section_course.save(update_fields=list(updates.keys()))

        latest_assignment = class_section.teaching_assignments.order_by('-assigned_at').first()
        if latest_assignment and section_course.instructor_id != latest_assignment.instructor_id:
            section_course.instructor = latest_assignment.instructor
            section_course.save(update_fields=['instructor'])

    return created, skipped


def ensure_class_sections_for_term(term: Term) -> Tuple[int, int]:
    """
    Ensure ClassSection entries exist for all SectionCourse rows in a term.
    Returns (created_count, skipped_count).
    """

    created = 0
    skipped = 0

    section_courses = SectionCourse.objects.filter(term=term).select_related('section')

    for sc in section_courses:
        defaults = {
            'capacity': sc.capacity or getattr(sc.section, 'capacity', 40),
            'schedule': sc.schedule,
            'platform_url': sc.platform_url,
            'is_active': sc.is_active,
            'start_date': sc.start_date,
            'end_date': sc.end_date,
        }

        class_section, was_created = ClassSection.objects.get_or_create(
            course=sc.course,
            term=term,
            section_code=sc.section.code,
            defaults=defaults,
        )

        if was_created:
            created += 1
        else:
            skipped += 1
            updates = {}

            if sc.schedule and not class_section.schedule:
                updates['schedule'] = sc.schedule
            if sc.platform_url and not class_section.platform_url:
                updates['platform_url'] = sc.platform_url
            if sc.start_date and not class_section.start_date:
                updates['start_date'] = sc.start_date
            if sc.end_date and not class_section.end_date:
                updates['end_date'] = sc.end_date
            if sc.capacity and class_section.capacity < sc.capacity:
                updates['capacity'] = sc.capacity

            if updates:
                for field, value in updates.items():
                    setattr(class_section, field, value)
                class_section.save(update_fields=list(updates.keys()))

    return created, skipped


def sync_all_existing_data() -> Tuple[int, int]:
    """
    Sync all existing courses and terms to create missing SectionCourse entries.
    Returns (created_count, skipped_count).
    """
    created = 0
    skipped = 0
    
    # Sync all existing courses
    courses = Course.objects.filter(
        suggested_year__isnull=False,
        suggested_term__isnull=False
    )
    for course in courses:
        c, s = sync_section_courses_for_course(course)
        created += c
        skipped += s
    
    # Sync all existing terms
    terms = Term.objects.all()
    for term in terms:
        c, s = sync_section_courses_for_term(term)
        created += c
        skipped += s

    # Backfill from legacy ClassSection records to ensure older data is synced
    cs_created, cs_skipped = sync_section_courses_from_class_sections()
    created += cs_created
    skipped += cs_skipped
    
    return created, skipped
