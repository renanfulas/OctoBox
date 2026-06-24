"""
ARQUIVO: gateway de pagamento com a Stripe.

POR QUE ELE EXISTE:
- isola a API da Stripe do resto do OctoBox.
- implementa a diretriz de idempotencia com a mesma lingua compartilhada da Signal Mesh.
"""

import stripe
from django.conf import settings
from django.db import connection
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


def create_checkout_session(
    payment: Payment, request, *, success_url: str | None = None, cancel_url: str | None = None
) -> str:
    if payment.status == 'paid':
        raise ValueError('Pagamento ja consta como PAGO no banco de dados.')

    idem_key = generate_idempotency_key(payment, 'checkout')
    metadata = {
        'payment_id': payment.id,
        'student_id': payment.student.id,
        'version_locked': payment.version,
        # Multi-tenant: o checkout roda em contexto de box, mas o webhook de
        # confirmacao chega no schema public. Sem carregar o schema do box aqui,
        # o reconcile faz SELECT em public e o Payment (TENANT_APP) some
        # ('relation does not exist'). Gravamos o schema do tenant ativo para o
        # router conseguir reabrir o schema_context certo na baixa.
        'box_schema': connection.schema_name,
    }

    product_name = 'Fatura Avulsa'
    if payment.enrollment and payment.enrollment.plan:
        product_name = f'Plano {payment.enrollment.plan.name} - {payment.installment_number}/{payment.installment_total}'

    # URLs de retorno parametrizaveis: o staff usa as rotas do catalogo (default),
    # o app do aluno passa as proprias rotas do /aluno/. Default preserva o
    # comportamento atual.
    if success_url is None:
        success_url = request.build_absolute_uri(reverse('checkout_success', args=[payment.id])) + '?session_id={CHECKOUT_SESSION_ID}'
    if cancel_url is None:
        cancel_url = request.build_absolute_uri(reverse('checkout_cancel', args=[payment.id]))

    # O aluno nao e um request.user autenticado do Django (auth por cookie proprio):
    # nesse caso o ator do audit e None. Staff continua com o proprio user.
    actor = request.user if getattr(getattr(request, 'user', None), 'is_authenticated', False) else None

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
            actor=actor,
            action='stripe_checkout_initiated',
            target=payment,
            description='Redirecionando para portal seguro da Stripe',
            metadata={'session_id': session.id, 'idempotency_key': idem_key},
        )
        return session.url
    except stripe.StripeError as exc:
        log_audit_event(
            actor=actor,
            action='stripe_checkout_failed',
            target=payment,
            description=f'Falha na malha da Stripe: {str(exc)}',
        )
        raise RuntimeError(f'Erro de comunicacao com a adquirente: {str(exc)}')


def refund_payment(payment: Payment) -> str:
    """
    Inicia o estorno do pagamento na Stripe. NAO da baixa no banco — a baixa
    oficial (status REFUNDED) vem do webhook charge.refunded (handler do router).

    Idempotente por payment+version via idempotency_key (re-clique nao duplica o
    estorno). Levanta:
    - ValueError se o pagamento nao tem vinculo Stripe (estorno deve ser manual).
    - RuntimeError em falha de comunicacao com a Stripe.
    """
    payment_intent_id = getattr(payment, 'stripe_payment_intent_id', '') or ''
    charge_id = getattr(payment, 'stripe_charge_id', '') or ''
    if not payment_intent_id and not charge_id:
        raise ValueError('Pagamento sem vinculo Stripe (payment_intent/charge) para estornar.')

    idem_key = generate_idempotency_key(payment, 'refund')
    refund_kwargs = {'idempotency_key': idem_key}
    if payment_intent_id:
        refund_kwargs['payment_intent'] = payment_intent_id
    else:
        refund_kwargs['charge'] = charge_id

    try:
        refund = stripe.Refund.create(**refund_kwargs)
        refund_id = getattr(refund, 'id', '') or ''
        log_audit_event(
            actor=None,
            action='stripe_refund_initiated',
            target=payment,
            description='Estorno iniciado no gateway Stripe',
            metadata={'refund_id': refund_id, 'idempotency_key': idem_key},
        )
        return refund_id
    except stripe.StripeError as exc:
        log_audit_event(
            actor=None,
            action='stripe_refund_failed',
            target=payment,
            description=f'Falha ao estornar na Stripe: {str(exc)}',
        )
        raise RuntimeError(f'Erro ao estornar na adquirente: {str(exc)}')


def get_stripe_payment_state(payment_intent_id: str) -> dict | None:
    """
    Le o estado atual de um PaymentIntent na Stripe para a reconciliacao Stripe<->DB.

    Retorna um dict normalizado {'pi_status', 'refunded', 'charge_id'} ou None se
    o PI nao existe / a Stripe falhar (a reconciliacao apenas reporta, nunca muta
    com base em leitura ausente). Isola o formato do SDK aqui — o caller so ve o dict.
    """
    if not payment_intent_id:
        return None
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id, expand=['latest_charge'])
    except stripe.StripeError:
        return None

    charge = getattr(intent, 'latest_charge', None)
    refunded = bool(getattr(charge, 'refunded', False)) if charge else False
    charge_id = getattr(charge, 'id', '') if charge else ''
    return {
        'pi_status': getattr(intent, 'status', '') or '',
        'refunded': refunded,
        'charge_id': charge_id or '',
    }


__all__ = [
    'create_checkout_session',
    'generate_idempotency_key',
    'get_stripe_payment_state',
    'refund_payment',
]
