"""
ARQUIVO: casos de uso dos workflows leves de plano.

POR QUE ELE EXISTE:
- Tira da camada historica do catalogo a orquestracao de criacao e edicao leve de plano.

O QUE ESTE ARQUIVO FAZ:
1. Cria plano com auditoria no mesmo fluxo.
2. Atualiza plano com trilha de campos alterados.

PONTOS CRITICOS:
- A camada de aplicacao nao pode depender de ORM, form ou view.
"""

import logging

from django.db import transaction
from django.utils import timezone

from .commands import MembershipPlanCommand, ReconcilePaymentCommand
from .ports import MembershipPlanAuditPort, MembershipPlanWriterPort, UnitOfWorkPort
from .results import MembershipPlanRecord

logger = logging.getLogger(__name__)


def execute_create_membership_plan_use_case(
    command: MembershipPlanCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    writer: MembershipPlanWriterPort,
    audit: MembershipPlanAuditPort,
) -> MembershipPlanRecord:
    def operation():
        result = writer.create(command)
        audit.record_created(command=command, result=result)
        return result

    return unit_of_work.run(operation)


def execute_update_membership_plan_use_case(
    command: MembershipPlanCommand,
    *,
    unit_of_work: UnitOfWorkPort,
    writer: MembershipPlanWriterPort,
    audit: MembershipPlanAuditPort,
) -> MembershipPlanRecord:
    def operation():
        result = writer.update(command)
        audit.record_updated(command=command, result=result)
        return result

    return unit_of_work.run(operation)


class ReconcilePaymentResult:
    __slots__ = ('payment_id', 'already_paid', 'reconciled')

    def __init__(self, *, payment_id: int, already_paid: bool, reconciled: bool):
        self.payment_id = payment_id
        self.already_paid = already_paid
        self.reconciled = reconciled


def execute_reconcile_payment_use_case(command: ReconcilePaymentCommand) -> ReconcilePaymentResult:
    """
    Reconcilia pagamento a partir de evento Stripe normalizado.
    Isolado do request web — chamado apenas pelo router da Signal Mesh.
    Importa os models aqui para manter o use case independente do Django no topo do módulo.
    """
    from finance.models import Payment, PaymentStatus
    from auditing import log_audit_event

    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(pk=command.payment_id)
        except Payment.DoesNotExist:
            logger.error(
                'ReconcilePayment: payment %s não encontrado. stripe_event=%s',
                command.payment_id,
                command.stripe_event_id,
            )
            raise

        if payment.status == PaymentStatus.PAID:
            return ReconcilePaymentResult(
                payment_id=payment.id,
                already_paid=True,
                reconciled=False,
            )

        if int(payment.amount * 100) != command.amount_cents:
            logger.error(
                'ReconcilePayment: inconsistência de valor. payment=%s esperado=%s recebido=%s',
                command.payment_id,
                int(payment.amount * 100),
                command.amount_cents,
            )
            raise ValueError(
                f'Valor divergente: esperado {int(payment.amount * 100)} cents, recebido {command.amount_cents} cents.'
            )

        payment.status = PaymentStatus.PAID
        payment.paid_at = timezone.now()
        payment.version += 1
        # Linkage Stripe: vincula a baixa ao charge real (auditoria/idempotencia/
        # estorno). Preserva valor existente quando o command nao trouxer o dado.
        payment.stripe_session_id = command.stripe_session_id or payment.stripe_session_id
        payment.stripe_payment_intent_id = (
            command.stripe_payment_intent_id or payment.stripe_payment_intent_id
        )
        payment.currency = command.currency or payment.currency
        payment.save(update_fields=[
            'status', 'paid_at', 'version',
            'stripe_session_id', 'stripe_payment_intent_id', 'currency',
            'updated_at',
        ])

        log_audit_event(
            actor=None,
            action='payment_reconciled_via_stripe',
            target=payment,
            description=f'Pagamento reconciliado via evento Stripe {command.stripe_event_id}',
            metadata={'stripe_event_id': command.stripe_event_id},
        )

    return ReconcilePaymentResult(
        payment_id=payment.id,
        already_paid=False,
        reconciled=True,
    )


class RefundPaymentResult:
    __slots__ = ('payment_id', 'already_refunded', 'refunded')

    def __init__(self, *, payment_id: int, already_refunded: bool, refunded: bool):
        self.payment_id = payment_id
        self.already_refunded = already_refunded
        self.refunded = refunded


def execute_refund_payment_from_stripe_use_case(
    *, payment_id: int, stripe_charge_id: str, stripe_event_id: str
) -> RefundPaymentResult:
    """
    Marca o Payment como REFUNDED a partir de um evento charge.refunded do Stripe.
    Idempotente (ja REFUNDED -> no-op) e com lock pessimista. Chamado pelo router
    JA dentro de schema_context(box) — o tenant e resolvido via StripePaymentRef.
    """
    from finance.models import Payment, PaymentStatus
    from auditing import log_audit_event

    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(pk=payment_id)
        except Payment.DoesNotExist:
            logger.error(
                'RefundPayment: payment %s nao encontrado. stripe_event=%s',
                payment_id, stripe_event_id,
            )
            raise

        if payment.status == PaymentStatus.REFUNDED:
            return RefundPaymentResult(payment_id=payment.id, already_refunded=True, refunded=False)

        payment.status = PaymentStatus.REFUNDED
        payment.version += 1
        if stripe_charge_id:
            payment.stripe_charge_id = stripe_charge_id
        payment.save(update_fields=['status', 'version', 'stripe_charge_id', 'updated_at'])

        log_audit_event(
            actor=None,
            action='payment_refunded_via_stripe',
            target=payment,
            description=f'Pagamento estornado via evento Stripe {stripe_event_id}',
            metadata={'stripe_event_id': stripe_event_id, 'stripe_charge_id': stripe_charge_id},
        )

    return RefundPaymentResult(payment_id=payment.id, already_refunded=False, refunded=True)


__all__ = [
    'execute_create_membership_plan_use_case',
    'execute_reconcile_payment_use_case',
    'execute_refund_payment_from_stripe_use_case',
    'execute_update_membership_plan_use_case',
    'ReconcilePaymentResult',
    'RefundPaymentResult',
]