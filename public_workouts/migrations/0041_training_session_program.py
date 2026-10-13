from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0040_training_sessions_and_push')]

    operations = [
        migrations.AddField(
            model_name='publicworkouttrainingsession',
            name='program',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='training_sessions', to='public_workouts.publicworkoutprogram',
            ),
        ),
        migrations.AddField(
            model_name='publicworkouttrainingsession',
            name='start_key',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
