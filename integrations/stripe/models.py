"""
ARQUIVO: modelo de persistência de eventos webhook da Stripe.

POR QUE ELE EXISTE:
- Garante que cada evento Stripe seja registrado antes de qualquer processamento.
- Permite observabilidade, retentativas e dead letter sem depender do retry automático da Stripe.
- Segue o padrão estabelecido em integrations/whatsapp/models.py.

O QUE ESTE ARQUIVO FAZ:
1. Persiste o envelope bruto do evento Stripe com idempotência por event_id.
2. Expõe register_failure() e mark_processed() usando a policy canônica da mesh.
3. Fornece lag_seconds() para o painel de observabilidade.

PONTOS CRITICOS:
- Nunca expor o payload bruto fora deste módulo sem normalização.
- event_id vem do campo id do evento Stripe (ex: evt_xxx) — é o idempotency key externo.
"""

from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel
from integrations.mesh import FAILURE_KIND_RETRYABLE, decide_retry


class PaymentWebhookStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    PROCESSED = 'processed', 'Processado'
    FAILED = 'failed', 'Falhou'


class PaymentWebhookEvent(TimeStampedModel):
    """
    Registro imutável de cada evento recebido da Stripe.
    Criado na borda (view), processado pelo router, nunca alterado pelo domínio.
    """

    event_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='ID do evento Stripe (evt_xxx). Garante idempotência.',
    )
    event_type = models.CharField(
        max_length=128,
        db_index=True,
        help_text='Tipo do evento Stripe (ex: checkout.session.completed).',
    )
    provider = models.CharField(max_length=50, default='stripe')
    payload = models.JSONField(
        help_text='Payload bruto normalizado. Não expor fora de integrations/stripe/.',
    )

    status = models.CharField(
        max_length=20,
        choices=PaymentWebhookStatus.choices,
        default=PaymentWebhookStatus.PENDING,
        db_index=True,
    )
    attempts = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error_message = models.TextField(null=True, blank=True)

    class Meta:
        app_label = 'integrations'
        db_table = 'stripe_payment_webhook_event'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['event_type', 'status']),
        ]

    def lag_seconds(self) -> float | None:
        """Segundos entre criação e processamento. None se ainda pendente."""
        if self.status == PaymentWebhookStatus.PROCESSED and self.updated_at:
            return (self.updated_at - self.created_at).total_seconds()
        return None

    def register_failure(self, *, failure_kind: str = '', error_message: str = '', reason: str = ''):
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
            PaymentWebhookStatus.PENDING if decision.should_retry else PaymentWebhookStatus.FAILED
        )
        self.save(update_fields=['attempts', 'last_error_message', 'next_retry_at', 'status', 'updated_at'])
        return decision

    def mark_processed(self):
        self.status = PaymentWebhookStatus.PROCESSED
        self.next_retry_at = None
        self.last_error_message = ''
        self.save(update_fields=['status', 'next_retry_at', 'last_error_message', 'updated_at'])


__all__ = ['PaymentWebhookEvent', 'PaymentWebhookStatus']
