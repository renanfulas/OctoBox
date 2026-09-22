from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('public_workouts', '0025_experiment_foundation'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PublicWorkoutAnalyticsCredential',
            new_name='PublicWorkoutStaffCredential',
        ),
    ]
