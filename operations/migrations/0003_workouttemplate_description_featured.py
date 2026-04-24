from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0002_workouttemplate_usage_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='workouttemplate',
            name='description',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='workouttemplate',
            name='is_featured',
            field=models.BooleanField(default=False),
        ),
    ]
