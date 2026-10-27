from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_identity', '0005_studentinvitationdelivery_encrypted_recipient'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentidentity',
            name='email_lookup_index',
            field=models.CharField(blank=True, db_index=True, default='', max_length=67),
        ),
    ]
