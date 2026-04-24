from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0003_workouttemplate_description_featured'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='workouttemplate',
            options={'ordering': ['-is_featured', '-is_active', '-usage_count', '-last_used_at', 'name', '-created_at']},
        ),
    ]
