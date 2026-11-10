from django.db import migrations, models


class Migration(migrations.Migration):
    """F2 offline-first: autoavaliação enviada pela fila offline não duplica."""

    dependencies = [
        ('public_workouts', '0049_commerce_email_lookup_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='publicworkoutassessment',
            name='idempotency_key',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
