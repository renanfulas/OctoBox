from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('public_workouts', '0046_rest_alert')]

    operations = [
        migrations.AddField(
            model_name='publicworkouttrainingset',
            name='duration_seconds',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
