import uuid

from django.db import models

from model_support.base import TimeStampedModel
from shared_support.crypto_fields import EncryptedCharField

from integrations.mesh import FAILURE_KIND_RETRYABLE, decide_retry

class WebhookDeliveryStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSED = 'processed', 'Processed'
    FAILED = 'failed', 'Failed'

class WebhookEvent(TimeStampedModel):
    """
    FIX 2: Webhook Idempotency & Backoff Engine.
    Prevents Evolution API (or any provider) from creating duplicate asynchronous queues.
    """
    event_id = models.CharField(max_length=255, unique=True, db_index=True, null=True, blank=True)
    webhook_fingerprint = models.CharField(max_length=64, unique=True, db_index=True, null=True, blank=True)
    provider = models.CharField(max_length=50)
    payload = models.JSONField()
    
    status = models.CharField(max_length=20, choices=WebhookDeliveryStatus.choices, default=WebhookDeliveryStatus.PENDING)
    
    attempts = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    last_error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'whatsapp_webhook_event'
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['webhook_fingerprint']),
        ]

    def register_failure(self, *, failure_kind: str, error_message: str = '', reason: str = ''):
        decision = decide_retry(
            failure_kind=failure_kind or FAILURE_KIND_RETRYABLE,
            attempts=self.attempts,
            max_attempts=self.max_retries,
            reason=reason,
        )

        self.attempts = decision.attempt_number
        self.last_error_message = error_message or reason
        self.next_retry_at = decision.next_retry_at
        self.status = (
            WebhookDeliveryStatus.PENDING if decision.should_retry else WebhookDeliveryStatus.FAILED
        )
        self.save(update_fields=['attempts', 'last_error_message', 'next_retry_at', 'status'])
        return decision

    def mark_processed(self):
        self.status = WebhookDeliveryStatus.PROCESSED
        self.next_retry_at = None
        self.last_error_message = ''
        self.save(update_fields=['status', 'next_retry_at', 'last_error_message'])

    def increment_retry_with_backoff(self):
        """
        Compatibilidade: delega o backoff para a policy canônica da mesh.
        """
        return self.register_failure(
            failure_kind=FAILURE_KIND_RETRYABLE,
            error_message='retry-scheduled',
            reason='retry-scheduled',
        )


class WhatsAppPollWebhookIntent(TimeStampedModel):
    """Tenant-local, encrypted inbox row for one authenticated poll vote."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        PROCESSED = 'processed', 'Processado'
        FAILED = 'failed', 'Falhou'

    provider = models.CharField(max_length=32, default='evolution')
    event_id = models.CharField(max_length=255)
    phone = EncryptedCharField(max_length=255, storage_max_length=2048)
    poll_title = models.CharField(max_length=255)
    option_voted = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=5)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'boxcore'
        db_table = 'boxcore_whatsapp_poll_intent'
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'event_id'],
                name='uq_whpoll_provider_event',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'next_retry_at'], name='whpoll_status_retry_idx'),
        ]

    def __str__(self):
        return f'{self.provider}:{self.event_id}'
