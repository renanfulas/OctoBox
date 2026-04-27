"""
ARQUIVO: gateway de pagamento com a Stripe.

POR QUE ELE EXISTE:
- isola a API da Stripe do resto do OctoBox.
- implementa a diretriz de idempotencia com a mesma lingua compartilhada da Signal Mesh.
"""

import stripe
from django.conf import settings
from django.urls import reverse

from auditing import log_audit_event
from finance.models import Payment
from integrations.mesh import build_idempotency_key

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'stripe-key-placeholder')


def generate_idempotency_key(payment: Payment, action: str) -> str:
    return build_idempotency_key(
        namespace='octobox',
        action=action,
        primary_reference=f'pay_{payment.id}',
        version_reference=str(payment.version),
    )


def create_checkout_session(payment: Payment, request) -> str:
    if payment.status == 'paid':
        raise ValueError('Pagamento ja consta como PAGO no banco de dados.')

    idem_key = generate_idempotency_key(payment, 'checkout')
    metadata = {
        'payment_id': payment.id,
        'student_id': payment.student.id,
        'version_locked': payment.version,
    }

    product_name = 'Fatura Avulsa'
    if payment.enrollment and payment.enrollment.plan:
        product_name = f'Plano {payment.enrollment.plan.name} - {payment.installment_number}/{payment.installment_total}'

    success_url = request.build_absolute_uri(reverse('checkout_success', args=[payment.id])) + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = request.build_absolute_uri(reverse('checkout_cancel', args=[payment.id]))

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'pix'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': product_name,
                        'description': payment.notes or f'Cobranca para {payment.student.full_name}',
                    },
                    'unit_amount': int(payment.amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(payment.student.id),
            metadata=metadata,
            idempotency_key=idem_key,
        )

        log_audit_event(
            actor=request.user,
            action='stripe_checkout_initiated',
            target=payment,
            description='Redirecionando para portal seguro da Stripe',
            metadata={'session_id': session.id, 'idempotency_key': idem_key},
        )
        return session.url
    except stripe.StripeError as exc:
        log_audit_event(
            actor=request.user,
            action='stripe_checkout_failed',
            target=payment,
            description=f'Falha na malha da Stripe: {str(exc)}',
        )
        raise RuntimeError(f'Erro de comunicacao com a adquirente: {str(exc)}')


__all__ = ['create_checkout_session', 'generate_idempotency_key']
