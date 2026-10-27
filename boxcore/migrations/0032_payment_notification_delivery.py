# Generated for the tenant-local payment notification outbox.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boxcore', '0031_workout_program_tracks'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentNotificationDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('logical_event_key', models.CharField(max_length=128)),
                ('channel', models.CharField(max_length=16)),
                ('recipient_key', models.CharField(max_length=96)),
                ('message_version', models.PositiveSmallIntegerField(default=1)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendente'),
                        ('leased', 'Reservado'),
                        ('provider_accepted', 'Aceito pelo provedor'),
                        ('delivered', 'Entregue'),
                        ('retry_wait', 'Aguardando nova tentativa'),
                        ('unknown', 'Resultado desconhecido'),
                        ('failed', 'Falhou'),
                        ('skipped', 'Ignorado'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=24,
                )),
                ('reason_code', models.CharField(blank=True, max_length=64)),
                ('attempt_count', models.PositiveSmallIntegerField(default=0)),
                ('available_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('lease_token', models.UUIDField(blank=True, null=True)),
                ('lease_expires_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('last_attempt_at', models.DateTimeField(blank=True, null=True)),
                ('provider', models.CharField(blank=True, max_length=24)),
                ('provider_message_id', models.CharField(blank=True, max_length=180)),
                ('provider_accepted_at', models.DateTimeField(blank=True, null=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('payment', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='notification_deliveries',
                    to='boxcore.payment',
                )),
            ],
            options={
                'ordering': ['available_at', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='paymentnotificationdelivery',
            index=models.Index(fields=['status', 'available_at'], name='pnd_status_due_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentnotificationdelivery',
            index=models.Index(fields=['status', 'lease_expires_at'], name='pnd_lease_exp_idx'),
        ),
        migrations.AddConstraint(
            model_name='paymentnotificationdelivery',
            constraint=models.UniqueConstraint(
                fields=('logical_event_key', 'channel', 'recipient_key', 'message_version'),
                name='uniq_payment_notification_delivery_target',
            ),
        ),
    ]
