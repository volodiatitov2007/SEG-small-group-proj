from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('allocations', '0003_alter_allocationrun_cohort_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Policy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('rules', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='policies', to='allocations.project',
                )),
            ],
            options={
                'ordering': ['name', 'pk'],
                'constraints': [
                    models.UniqueConstraint(fields=('project', 'name'), name='unique_policy_name_per_project'),
                ],
            },
        ),
    ]
