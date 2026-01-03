from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_student_number'),
        ('classes', '0002_program_structure'),
    ]

    operations = [
        migrations.AlterField(
            model_name='class',
            name='instructor',
            field=models.ForeignKey(blank=True, help_text='Instructor for this class (can be unassigned until approved)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='taught_classes', to='users.user'),
        ),
        migrations.CreateModel(
            name='InstructorApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('note', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('class_ref', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instructor_applications', to='classes.class')),
                ('instructor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_applications', to='users.user')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_applications', to='users.user')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('class_ref', 'instructor')},
            },
        ),
    ]
