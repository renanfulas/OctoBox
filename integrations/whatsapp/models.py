import uuid
from django.db import models
from model_support.base import TimeStampedModel

class WebhookDeliveryStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSED = 'processed', 'Processed'
    FAILED = 'failed', 'Failed'

class WebhookEvent(TimeStampedModel):
    """
    FIX 2: Webhook Idempotency & Backoff Engine.
    Prevents Evolution API (or any provider) from creating duplicate asynchronous queues.
    """
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
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
            models.Index(fields=['status', 'next_retry_at'])
        ]

    def increment_retry_with_backoff(self):
        """
        Calcula o Backoff Exponencial (2^attempts * base_delay)
        """
        import datetime
        from django.utils import timezone
        
        self.attempts += 1
        if self.attempts >= self.max_retries:
            self.status = WebhookDeliveryStatus.FAILED
        else:
            base_delay_seconds = 10
            delay = base_delay_seconds * (2 ** (self.attempts - 1))
            self.next_retry_at = timezone.now() + datetime.timedelta(seconds=delay)
        self.save(update_fields=['attempts', 'status', 'next_retry_at'])
