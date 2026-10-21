from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0021_testimonials')]

    operations = [
        migrations.CreateModel(
            name='PublicWorkoutMetricSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_date', models.DateField(db_index=True)),
                ('schema_version', models.PositiveSmallIntegerField(default=1)),
                ('payload', models.JSONField(default=dict)),
                ('captured_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-metric_date', '-captured_at'],
                'constraints': [models.UniqueConstraint(fields=('metric_date', 'schema_version'), name='unique_public_workout_metric_snapshot_day_version')],
            },
        ),
    ]
