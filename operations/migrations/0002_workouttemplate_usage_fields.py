from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0001_workout_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='workouttemplate',
            name='usage_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='workouttemplate',
            name='last_used_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
