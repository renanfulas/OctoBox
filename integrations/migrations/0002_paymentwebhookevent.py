from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_id', models.CharField(
                    db_index=True,
                    help_text='ID do evento Stripe (evt_xxx). Garante idempotência.',
                    max_length=255,
                    unique=True,
                )),
                ('event_type', models.CharField(
                    db_index=True,
                    help_text='Tipo do evento Stripe (ex: checkout.session.completed).',
                    max_length=128,
                )),
                ('provider', models.CharField(default='stripe', max_length=50)),
                ('payload', models.JSONField(
                    help_text='Payload bruto normalizado. Não expor fora de integrations/stripe/.',
                )),
                ('status', models.CharField(
                    choices=[('pending', 'Pendente'), ('processed', 'Processado'), ('failed', 'Falhou')],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('attempts', models.IntegerField(default=0)),
                ('max_retries', models.IntegerField(default=5)),
                ('next_retry_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('last_error_message', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'stripe_payment_webhook_event',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status', 'next_retry_at'], name='stripe_wh_status_retry_idx'),
                    models.Index(fields=['event_type', 'status'], name='stripe_wh_type_status_idx'),
                ],
            },
        ),
    ]
