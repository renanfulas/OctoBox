"""Add an additive tenant-local exact-lookup index for encrypted Student CPF."""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("boxcore", "0033_encrypted_char_storage_capacity"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="cpf_lookup_index",
            field=models.CharField(blank=True, default="", max_length=67),
        ),
        AddIndexConcurrently(
            model_name="student",
            index=models.Index(
                fields=["cpf_lookup_index"],
                condition=~models.Q(cpf_lookup_index=""),
                name="student_cpf_lu_idx",
            ),
        ),
    ]
