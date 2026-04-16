import uuid

from django.db import models

from model_support.base import TimeStampedModel

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
