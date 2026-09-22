from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0010_seed_public_workout_professionals')]

    operations = [
        migrations.AddField(
            model_name='publicworkoutnutritionprofile', name='objetivo',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='publicworkoutnutritionprofile', name='medicamentos',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='publicworkoutnutritionprofile', name='historico',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='publicworkoutnutritionprofile', name='consent_health_processing_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='publicworkoutnutritionprofile', name='consent_version',
            field=models.CharField(blank=True, max_length=24),
        ),
    ]
