# Generated for the Curva set-role rollout.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0027_rename_analytics_credential_to_staff_credential')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutloadlog',
            name='set_role',
            field=models.CharField(
                choices=[
                    ('warmup', 'Aquecimento'),
                    ('feeder', 'Aproximação'),
                    ('top_set', 'Série principal'),
                    ('max_set', 'Esforço máximo'),
                    ('legacy_unknown', 'Histórico anterior (não classificado)'),
                ],
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='publicworkoutloadlog',
            index=models.Index(
                fields=['account', 'set_role', 'movement_slug', 'performed_on'],
                name='pwll_acct_role_move_day_idx',
            ),
        ),
    ]
