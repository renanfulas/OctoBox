from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0042_training_session_outcome')]

    operations = [
        migrations.AlterField(
            model_name='publicworkouttrainingsession', name='outcome',
            field=models.CharField(blank=True, choices=[
                ('completed', 'Concluído'), ('partial', 'Parcial'),
                ('cancelled', 'Cancelado'), ('abandoned', 'Abandonado'),
            ], max_length=12),
        ),
        migrations.AddField(
            model_name='publicworkouttrainingset', name='status',
            field=models.CharField(choices=[('performed', 'Realizada'), ('skipped', 'Pulada')], default='performed', max_length=12),
        ),
        migrations.AddField(
            model_name='publicworkouttrainingset', name='stage_id',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='publicworkouttrainingset', name='stage_ordinal',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='publicworkouttrainingset', name='load_log',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='guided_training_sets', to='public_workouts.publicworkoutloadlog'),
        ),
        migrations.CreateModel(
            name='PublicWorkoutTrainingSetRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('command_key', models.UUIDField(unique=True)),
                ('before', models.JSONField(default=dict)),
                ('after', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('training_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name='revisions', to='public_workouts.publicworkouttrainingset')),
            ],
        ),
    ]
