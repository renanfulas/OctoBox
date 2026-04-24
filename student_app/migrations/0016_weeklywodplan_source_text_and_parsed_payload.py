from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_app', '0015_weeklywodplan_dayplan_planblock_planmovement_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklywodplan',
            name='parsed_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='weeklywodplan',
            name='source_text',
            field=models.TextField(blank=True),
        ),
    ]
