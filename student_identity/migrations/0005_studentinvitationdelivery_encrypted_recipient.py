from django.db import migrations
from shared_support.crypto_fields import EncryptedCharField


class Migration(migrations.Migration):

    dependencies = [
        ("student_identity", "0004_alter_studentconsent_document_kind_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentinvitationdelivery",
            name="recipient",
            field=EncryptedCharField(max_length=255, storage_max_length=2048),
        ),
    ]
