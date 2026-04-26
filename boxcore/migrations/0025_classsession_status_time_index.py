from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0024_classsession_class_type'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='classsession',
            index=models.Index(fields=['status', 'scheduled_at'], name='class_session_status_time'),
        ),
    ]
