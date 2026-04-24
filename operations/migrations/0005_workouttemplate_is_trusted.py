from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0004_alter_workouttemplate_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='workouttemplate',
            name='is_trusted',
            field=models.BooleanField(default=False),
        ),
    ]
