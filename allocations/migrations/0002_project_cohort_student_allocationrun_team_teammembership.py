from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('allocations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projects', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Cohort',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_filename', models.CharField(max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('columns', models.JSONField(default=list)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cohorts', to='allocations.project')),
            ],
        ),
        migrations.CreateModel(
            name='AllocationRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('policy_snapshot', models.JSONField(default=dict)),
                ('status', models.CharField(choices=[('ok', 'Allocated'), ('infeasible', 'Known infeasible'), ('timeout', 'None found in time')], max_length=12)),
                ('message', models.TextField(blank=True)),
                ('violations', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('duration_seconds', models.FloatField(blank=True, null=True)),
                ('cohort', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='runs', to='allocations.cohort')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='allocations.project')),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('gender', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('ethnicity', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('c_score', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('extra', models.JSONField(default=dict)),
                ('cohort', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='allocations.cohort')),
            ],
            options={'ordering': ['last_name', 'first_name', 'email']},
        ),
        migrations.AddConstraint(
            model_name='student',
            constraint=models.UniqueConstraint(fields=('cohort', 'email'), name='unique_email_per_cohort'),
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='allocations.allocationrun')),
            ],
            options={'ordering': ['name', 'pk']},
        ),
        migrations.CreateModel(
            name='TeamMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='team_memberships', to='allocations.student')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='allocations.team')),
            ],
        ),
        migrations.AddConstraint(
            model_name='teammembership',
            constraint=models.UniqueConstraint(fields=('team', 'student'), name='unique_member'),
        ),
    ]
