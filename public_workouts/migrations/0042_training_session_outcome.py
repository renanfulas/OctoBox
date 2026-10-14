from django.db import migrations, models


def backfill_completed(apps, schema_editor):
    session = apps.get_model('public_workouts', 'PublicWorkoutTrainingSession')
    for row in session.objects.filter(completed_at__isnull=False).only('id', 'completed_at').iterator():
        session.objects.filter(pk=row.pk).update(ended_at=row.completed_at, outcome='completed')


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0041_training_session_program')]

    operations = [
        migrations.AddField(
            model_name='publicworkouttrainingsession', name='ended_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='publicworkouttrainingsession', name='outcome',
            field=models.CharField(blank=True, choices=[('completed', 'Concluído'), ('partial', 'Parcial')], max_length=12),
        ),
        migrations.RunPython(backfill_completed, migrations.RunPython.noop),
    ]
