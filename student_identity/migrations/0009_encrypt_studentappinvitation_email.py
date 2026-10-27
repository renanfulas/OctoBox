from django.db import migrations
from shared_support.crypto_fields import EncryptedEmailField


class Migration(migrations.Migration):

    dependencies = [
        ('student_identity', '0008_studentappinvitation_email_lookup_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentappinvitation',
            name='invited_email',
            field=EncryptedEmailField(
                blank=True,
                max_length=254,
                storage_max_length=2048,
                writer_enabled_setting='STUDENT_APP_INVITATION_EMAIL_ENCRYPTION_WRITE_READY',
            ),
        ),
    ]
