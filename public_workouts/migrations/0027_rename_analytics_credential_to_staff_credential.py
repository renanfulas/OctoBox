from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('public_workouts', '0026_merge_20260922_2009'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PublicWorkoutAnalyticsCredential',
            new_name='PublicWorkoutStaffCredential',
        ),
    ]
