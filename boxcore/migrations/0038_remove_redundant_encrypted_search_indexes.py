"""Remove indexes/uniqueness that cannot apply to randomized ciphertext."""

import shared_support.crypto_fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("boxcore", "0037_payment_notification_delivery_event"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="phone",
            field=shared_support.crypto_fields.EncryptedCharField(
                max_length=255,
                storage_max_length=2048,
                verbose_name="WhatsApp",
            ),
        ),
        migrations.AlterField(
            model_name="studentintake",
            name="phone",
            field=shared_support.crypto_fields.EncryptedCharField(
                max_length=255,
                storage_max_length=2048,
            ),
        ),
        migrations.AlterField(
            model_name="studentintake",
            name="email",
            field=shared_support.crypto_fields.EncryptedCharField(
                blank=True,
                max_length=255,
                storage_max_length=2048,
            ),
        ),
        migrations.AlterField(
            model_name="whatsappcontact",
            name="phone",
            field=shared_support.crypto_fields.EncryptedCharField(
                max_length=255,
                storage_max_length=2048,
            ),
        ),
    ]
