from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('student_app', '0021_wodgenerationcreditledger'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sessionworkoutblock',
            name='kind',
            field=models.CharField(
                choices=[
                    ('warmup', 'Aquecimento'),
                    ('strength', 'Forca'),
                    ('skill', 'Skill'),
                    ('metcon', 'Metcon'),
                    ('mobility', 'Mobilidade'),
                    ('cooldown', 'Cooldown'),
                    ('custom', 'Livre'),
                ],
                default='custom',
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='sessionworkoutblock',
            name='timecap_min',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sessionworkoutblock',
            name='rounds',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sessionworkoutblock',
            name='interval_seconds',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sessionworkoutblock',
            name='score_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('for_time', 'For time'),
                    ('amrap', 'AMRAP'),
                    ('emom', 'EMOM'),
                    ('rounds_reps', 'Rounds e reps'),
                    ('load', 'Carga'),
                ],
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='sessionworkoutblock',
            name='format_spec',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='sessionworkoutmovement',
            name='reps_spec',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='sessionworkoutmovement',
            name='load_spec',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='sessionworkoutmovement',
            name='is_scaled_alternative',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='planblock',
            name='score_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('for_time', 'For time'),
                    ('amrap', 'AMRAP'),
                    ('emom', 'EMOM'),
                    ('rounds_reps', 'Rounds e reps'),
                    ('load', 'Carga'),
                ],
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='planblock',
            name='format_spec',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='planmovement',
            name='is_scaled_alternative',
            field=models.BooleanField(default=False),
        ),
    ]
