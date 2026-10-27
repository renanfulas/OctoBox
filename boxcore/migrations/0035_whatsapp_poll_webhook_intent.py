"""Create a tenant-local encrypted inbox for authenticated WhatsApp poll votes."""

import shared_support.crypto_fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('boxcore', '0034_student_cpf_lookup_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='WhatsAppPollWebhookIntent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.CharField(default='evolution', max_length=32)),
                ('event_id', models.CharField(max_length=255)),
                ('phone', shared_support.crypto_fields.EncryptedCharField(max_length=255, storage_max_length=2048)),
                ('poll_title', models.CharField(max_length=255)),
                ('option_voted', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('pending', 'Pendente'), ('processed', 'Processado'), ('failed', 'Falhou')], default='pending', max_length=20)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('max_retries', models.PositiveSmallIntegerField(default=5)),
                ('next_retry_at', models.DateTimeField(blank=True, null=True)),
                ('last_error_code', models.CharField(blank=True, max_length=64)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'boxcore_whatsapp_poll_intent',
                'constraints': [
                    models.UniqueConstraint(fields=('provider', 'event_id'), name='uq_whpoll_provider_event'),
                ],
                'indexes': [
                    models.Index(fields=['status', 'next_retry_at'], name='whpoll_status_retry_idx'),
                ],
            },
        ),
    ]
