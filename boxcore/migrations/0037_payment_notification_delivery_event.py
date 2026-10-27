"""Persist provider delivery receipts without storing webhook payload PII."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('boxcore', '0036_payment_notification_dedupe_metrics'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentNotificationDeliveryEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider_event_id', models.CharField(max_length=120, unique=True)),
                ('provider', models.CharField(default='resend', max_length=24)),
                ('event_type', models.CharField(db_index=True, max_length=64)),
                ('occurred_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('delivery', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='provider_events',
                    to='boxcore.paymentnotificationdelivery',
                )),
            ],
            options={
                'ordering': ['-occurred_at', '-id'],
            },
        ),
    ]
