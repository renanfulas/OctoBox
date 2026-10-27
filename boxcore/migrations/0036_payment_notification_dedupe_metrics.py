"""Track durable notification enqueue replays for C3 operations metrics."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('boxcore', '0035_whatsapp_poll_webhook_intent'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentnotificationdelivery',
            name='duplicate_suppressed_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
