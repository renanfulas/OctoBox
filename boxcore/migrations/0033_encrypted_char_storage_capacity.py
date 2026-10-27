"""Expand physical capacity for authenticated encrypted-field envelopes.

The model/form max_length stays 255. This migration only widens tenant-local
storage to fit the versioned Fernet envelope introduced by the reader-first
transition; it does not rewrite existing values.
"""

import shared_support.crypto_fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("boxcore", "0032_payment_notification_delivery"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="phone",
            field=shared_support.crypto_fields.EncryptedCharField(
                max_length=255,
                storage_max_length=2048,
                unique=True,
                verbose_name="WhatsApp",
            ),
        ),
        migrations.AlterField(
            model_name="student",
            name="cpf",
            field=shared_support.crypto_fields.EncryptedCharField(
                blank=True,
                max_length=255,
                storage_max_length=2048,
            ),
        ),
        migrations.AlterField(
            model_name="studentintake",
            name="phone",
            field=shared_support.crypto_fields.EncryptedCharField(
                db_index=True,
                max_length=255,
                storage_max_length=2048,
            ),
        ),
        migrations.AlterField(
            model_name="studentintake",
            name="email",
            field=shared_support.crypto_fields.EncryptedCharField(
                blank=True,
                db_index=True,
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
                unique=True,
            ),
        ),
    ]
