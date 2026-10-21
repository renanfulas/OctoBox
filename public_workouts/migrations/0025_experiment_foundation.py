from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0024_analytics_credentials')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutExperiment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('key', models.SlugField(max_length=80, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('hypothesis', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Rascunho'), ('running', 'Em execução'), ('paused', 'Pausado'), ('completed', 'Concluído')], db_index=True, default='draft', max_length=12)),
                ('primary_metric', models.CharField(default='first_payment', max_length=40)),
                ('conversion_days', models.PositiveSmallIntegerField(default=7)),
                ('minimum_sample_size', models.PositiveIntegerField(default=100)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('winner_variant_key', models.SlugField(blank=True, max_length=80)),
            ],
            options={
                'ordering': ['-created_at'],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(('conversion_days__gte', 1), ('conversion_days__lte', 30)), name='public_workout_experiment_conversion_days_range'),
                    models.CheckConstraint(condition=models.Q(('minimum_sample_size__gte', 1)), name='public_workout_experiment_minimum_sample_positive'),
                ],
            },
        ),
        migrations.CreateModel(
            name='PublicWorkoutExperimentVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('key', models.SlugField(max_length=80)),
                ('name', models.CharField(max_length=120)),
                ('allocation_weight', models.PositiveIntegerField(default=1)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='public_workouts.publicworkoutexperiment')),
            ],
            options={
                'ordering': ['experiment_id', 'created_at'],
                'constraints': [
                    models.UniqueConstraint(fields=('experiment', 'key'), name='unique_public_workout_experiment_variant_key'),
                    models.CheckConstraint(condition=models.Q(('allocation_weight__gte', 1)), name='public_workout_experiment_variant_weight_positive'),
                ],
            },
        ),
        migrations.CreateModel(
            name='PublicWorkoutExperimentAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('acquisition_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiment_assignments', to='public_workouts.publicworkoutacquisitionsession')),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assignments', to='public_workouts.publicworkoutexperiment')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assignments', to='public_workouts.publicworkoutexperimentvariant')),
            ],
            options={
                'ordering': ['-assigned_at'],
                'constraints': [
                    models.UniqueConstraint(fields=('experiment', 'acquisition_session'), name='unique_public_workout_experiment_session_assignment'),
                ],
            },
        ),
    ]
