from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_identity', '0006_studentappinvitation_onboarding_journey_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentidentity',
            name='photo_url',
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
