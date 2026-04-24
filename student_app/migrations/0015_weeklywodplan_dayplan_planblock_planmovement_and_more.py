from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('student_app', '0014_studentprofilechangerequest'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WeeklyWodPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('week_start', models.DateField()),
                ('label', models.CharField(blank=True, max_length=140)),
                ('status', models.CharField(choices=[('draft', 'Rascunho'), ('confirmed', 'Confirmado')], default='draft', max_length=24)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='weekly_wod_plans_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-week_start', '-created_at', '-id'],
                'indexes': [models.Index(fields=['status', '-week_start'], name='weekly_wod_plan_status_week')],
            },
        ),
        migrations.CreateModel(
            name='ReplicationBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('class_type_filter', models.JSONField(blank=True, default=list)),
                ('sessions_targeted', models.PositiveIntegerField(default=0)),
                ('sessions_created', models.PositiveIntegerField(default=0)),
                ('undone_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='weekly_wod_replication_batches_created', to=settings.AUTH_USER_MODEL)),
                ('weekly_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replication_batches', to='student_app.weeklywodplan')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='DayPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('weekday', models.PositiveSmallIntegerField(choices=[(0, 'Segunda'), (1, 'Terca'), (2, 'Quarta'), (3, 'Quinta'), (4, 'Sexta'), (5, 'Sabado'), (6, 'Domingo')])),
                ('sort_order', models.PositiveSmallIntegerField(default=1)),
                ('weekly_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='days', to='student_app.weeklywodplan')),
            ],
            options={
                'ordering': ['sort_order', 'weekday', 'id'],
                'constraints': [
                    models.UniqueConstraint(fields=('weekly_plan', 'weekday'), name='unique_weekly_wod_plan_weekday'),
                    models.UniqueConstraint(fields=('weekly_plan', 'sort_order'), name='unique_weekly_wod_plan_day_order'),
                ],
            },
        ),
        migrations.CreateModel(
            name='PlanBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(choices=[('warmup', 'Aquecimento'), ('strength', 'Forca'), ('skill', 'Skill'), ('metcon', 'WOD / Metcon'), ('cooldown', 'Cooldown'), ('mobility', 'Mobilidade'), ('custom', 'Livre')], default='custom', max_length=24)),
                ('title', models.CharField(blank=True, max_length=120)),
                ('notes', models.TextField(blank=True)),
                ('timecap_min', models.PositiveIntegerField(blank=True, null=True)),
                ('rounds', models.PositiveIntegerField(blank=True, null=True)),
                ('interval_seconds', models.PositiveIntegerField(blank=True, null=True)),
                ('sort_order', models.PositiveIntegerField(default=1)),
                ('day_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocks', to='student_app.dayplan')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
                'constraints': [models.UniqueConstraint(fields=('day_plan', 'sort_order'), name='unique_day_plan_block_order')],
            },
        ),
        migrations.CreateModel(
            name='PlanMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('movement_slug', models.SlugField(blank=True, max_length=64)),
                ('movement_label_raw', models.CharField(max_length=120)),
                ('sets', models.PositiveIntegerField(blank=True, null=True)),
                ('reps_spec', models.CharField(blank=True, max_length=64)),
                ('load_spec', models.CharField(blank=True, max_length=64)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('sort_order', models.PositiveIntegerField(default=1)),
                ('plan_block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movements', to='student_app.planblock')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
                'constraints': [models.UniqueConstraint(fields=('plan_block', 'sort_order'), name='unique_plan_block_movement_order')],
            },
        ),
    ]
