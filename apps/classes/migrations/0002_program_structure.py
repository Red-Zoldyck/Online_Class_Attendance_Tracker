from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("classes", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Program",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(db_index=True, max_length=20, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="YearLevel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveSmallIntegerField()),
                (
                    "program",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="year_levels", to="classes.program"),
                ),
            ],
            options={
                "ordering": ["program__code", "number"],
                "unique_together": {("program", "number")},
            },
        ),
        migrations.CreateModel(
            name="Term",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "term",
                    models.CharField(choices=[("1", "1st Sem"), ("2", "2nd Sem")], max_length=1),
                ),
                ("school_year", models.CharField(help_text="Format: 2025-2026", max_length=9)),
                (
                    "program",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="terms", to="classes.program"),
                ),
                (
                    "year_level",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="terms", to="classes.yearlevel"),
                ),
            ],
            options={
                "ordering": ["program__code", "school_year", "year_level__number", "term"],
                "unique_together": {("program", "year_level", "term", "school_year")},
            },
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20)),
                ("title", models.CharField(max_length=200)),
                ("units", models.DecimalField(decimal_places=1, default=3, max_digits=4)),
                ("suggested_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "suggested_term",
                    models.CharField(blank=True, choices=[("1", "1st Sem"), ("2", "2nd Sem")], max_length=1, null=True),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "program",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="courses", to="classes.program"),
                ),
            ],
            options={
                "ordering": ["program__code", "code"],
                "unique_together": {("program", "code")},
            },
        ),
        migrations.CreateModel(
            name="ClassSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section_code", models.CharField(help_text="e.g., CS101-A", max_length=20)),
                ("capacity", models.PositiveIntegerField(default=40)),
                ("schedule", models.CharField(help_text="e.g., Mon/Wed 10:00-11:30", max_length=200)),
                ("platform_url", models.URLField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="classes.course"),
                ),
                (
                    "term",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="classes.term"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("course", "term", "section_code")},
            },
        ),
        migrations.CreateModel(
            name="TeachingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "instructor",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teaching_sections", to="users.user"),
                ),
                (
                    "section",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teaching_assignments", to="classes.classsection"),
                ),
            ],
            options={
                "ordering": ["-assigned_at"],
                "unique_together": {("section", "instructor")},
            },
        ),
    ]
