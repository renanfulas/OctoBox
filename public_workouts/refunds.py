"""Garantia comercial de sete dias, com elegibilidade e execução auditáveis."""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .contracts import REFUND_GUARANTEE_DAYS
from .models import (
    PublicWorkoutGuaranteeModel,
    PublicWorkoutPaymentStatus,
    PublicWorkoutRefundRequest,
    PublicWorkoutRefundRequestStatus,
)


class RefundNotEligibleError(ValueError):
    pass


logger = logging.getLogger(__name__)


def get_refund_eligibility(subscription) -> dict:
    payment = subscription.payments.filter(
        status=PublicWorkoutPaymentStatus.PAID, paid_at__isnull=False,
    ).order_by('paid_at').first()
    deadline = payment.paid_at + timedelta(days=REFUND_GUARANTEE_DAYS) if payment else None
    existing = PublicWorkoutRefundRequest.objects.filter(subscription=subscription).first()
    eligible = bool(
        subscription.guarantee_model == PublicWorkoutGuaranteeModel.REFUND_GUARANTEE
        and payment and deadline >= timezone.now()
        and (existing is None or existing.status in (
            PublicWorkoutRefundRequestStatus.REJECTED,
            PublicWorkoutRefundRequestStatus.FAILED,
        ))
    )
    return {
        'eligible': eligible,
        'deadline': deadline,
        'request': existing,
        'payment_confirmed': payment is not None,
    }


def submit_refund_request(*, subscription, reason: str = '') -> PublicWorkoutRefundRequest:
    if subscription.guarantee_model != PublicWorkoutGuaranteeModel.REFUND_GUARANTEE:
        raise RefundNotEligibleError('assinatura sem garantia de reembolso')
    payment = subscription.payments.filter(
        status=PublicWorkoutPaymentStatus.PAID, paid_at__isnull=False,
    ).order_by('paid_at').first()
    if payment is None:
        raise RefundNotEligibleError('pagamento ainda nao confirmado')
    if payment.paid_at < timezone.now() - timedelta(days=REFUND_GUARANTEE_DAYS):
        raise RefundNotEligibleError('prazo da garantia encerrado')
    request_obj, created = PublicWorkoutRefundRequest.objects.get_or_create(
        subscription=subscription,
        defaults={'payment': payment, 'reason': reason.strip()[:2000]},
    )
    if not created and request_obj.status in (
        PublicWorkoutRefundRequestStatus.REJECTED,
        PublicWorkoutRefundRequestStatus.FAILED,
    ):
        request_obj.status = PublicWorkoutRefundRequestStatus.REQUESTED
        request_obj.reason = reason.strip()[:2000]
        request_obj.last_error = ''
        request_obj.requested_at = timezone.now()
        request_obj.save(update_fields=['status', 'reason', 'last_error', 'requested_at', 'updated_at'])
    logger.info(
        'curva_refund_requested request_id=%s subscription_id=%s payment_id=%s recreated=%s',
        request_obj.pk, subscription.pk, payment.pk, not created,
    )
    return request_obj


def process_refund_request(refund_request_id: int) -> PublicWorkoutRefundRequest:
    """Executa reembolso total e cancela renovacao; idempotente pelo request."""
    import stripe

    secret_key = str(getattr(settings, 'STRIPE_SECRET_KEY', '') or '').strip()
    if not secret_key:
        raise RuntimeError('STRIPE_SECRET_KEY nao configurada')
    stripe.api_key = secret_key
    with transaction.atomic():
        request_obj = PublicWorkoutRefundRequest.objects.select_for_update().select_related(
            'payment', 'subscription',
        ).get(pk=refund_request_id)
        if request_obj.status == PublicWorkoutRefundRequestStatus.REFUNDED:
            return request_obj
        request_obj.status = PublicWorkoutRefundRequestStatus.PROCESSING
        request_obj.last_error = ''
        request_obj.save(update_fields=['status', 'last_error', 'updated_at'])

    try:
        invoice = stripe.Invoice.retrieve(request_obj.payment.stripe_invoice_id)
        payment_intent = invoice.get('payment_intent') if isinstance(invoice, dict) else invoice.payment_intent
        if not payment_intent:
            raise RuntimeError('invoice sem payment_intent reembolsavel')
        refund = stripe.Refund.create(
            payment_intent=payment_intent,
            reason='requested_by_customer',
            idempotency_key=f'curva-guarantee-{request_obj.pk}',
        )
        if request_obj.subscription.stripe_subscription_id:
            stripe.Subscription.cancel(request_obj.subscription.stripe_subscription_id)
    except Exception as exc:
        PublicWorkoutRefundRequest.objects.filter(pk=request_obj.pk).update(
            status=PublicWorkoutRefundRequestStatus.FAILED,
            last_error=str(exc)[:255], processed_at=timezone.now(),
        )
        logger.exception(
            'curva_refund_failed request_id=%s subscription_id=%s error_type=%s',
            request_obj.pk, request_obj.subscription_id, type(exc).__name__,
        )
        raise

    from .billing import mark_subscription_canceled
    request_obj.payment.status = PublicWorkoutPaymentStatus.REFUNDED
    request_obj.payment.save(update_fields=['status', 'updated_at'])
    mark_subscription_canceled(request_obj.subscription, reason='garantia de 7 dias exercida')
    request_obj.status = PublicWorkoutRefundRequestStatus.REFUNDED
    request_obj.stripe_refund_id = refund.get('id') if isinstance(refund, dict) else refund.id
    request_obj.processed_at = timezone.now()
    request_obj.last_error = ''
    request_obj.save(update_fields=[
        'status', 'stripe_refund_id', 'processed_at', 'last_error', 'updated_at',
    ])
    logger.info(
        'curva_refund_completed request_id=%s subscription_id=%s payment_id=%s',
        request_obj.pk, request_obj.subscription_id, request_obj.payment_id,
    )
    return request_obj


__all__ = [
    'RefundNotEligibleError', 'get_refund_eligibility',
    'process_refund_request', 'submit_refund_request',
]
