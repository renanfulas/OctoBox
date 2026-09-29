from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0011_alter_smartplangateevent_actor_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workouttemplateblock',
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
            model_name='workouttemplateblock',
            name='timecap_min',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workouttemplateblock',
            name='rounds',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workouttemplateblock',
            name='interval_seconds',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workouttemplateblock',
            name='score_type',
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name='workouttemplateblock',
            name='format_spec',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='workouttemplatemovement',
            name='reps_spec',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='workouttemplatemovement',
            name='load_spec',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='workouttemplatemovement',
            name='is_scaled_alternative',
            field=models.BooleanField(default=False),
        ),
    ]
