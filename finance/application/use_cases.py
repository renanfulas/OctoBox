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
        payment.save(update_fields=['status', 'paid_at', 'version', 'updated_at'])

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


__all__ = [
    'execute_create_membership_plan_use_case',
    'execute_reconcile_payment_use_case',
    'execute_update_membership_plan_use_case',
    'ReconcilePaymentResult',
]