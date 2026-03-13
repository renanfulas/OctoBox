"""
ARQUIVO: regras puras de agenda financeira do aluno.

POR QUE ELE EXISTE:
- Centraliza o plano comercial de parcelas, recorrencia e regeneracao sem depender de ORM ou timezone do Django.

O QUE ESTE ARQUIVO FAZ:
1. Avanca vencimentos conforme o ciclo de cobranca.
2. Monta o plano puro de criacao de cobrancas para single, installments e recurring.
3. Define a progressao comercial de uma cobranca regenerada.

PONTOS CRITICOS:
- Essas regras afetam parcelamento, recorrencia e regeneracao de cobrança.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


def shift_month(source_date: date, month_delta: int) -> date:
    month_index = source_date.month - 1 + month_delta
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    return source_date.replace(year=year, month=month, day=1)


def advance_due_date(*, start_date: date, step: int, billing_cycle: str) -> date:
    if step == 0:
        return start_date
    if billing_cycle == 'weekly':
        return start_date + timedelta(days=7 * step)
    if billing_cycle == 'quarterly':
        return shift_month(start_date, step * 3)
    if billing_cycle == 'yearly':
        return shift_month(start_date, step * 12)
    return shift_month(start_date, step)


@dataclass(frozen=True, slots=True)
class PlannedPayment:
    due_date: date
    amount: Decimal
    installment_number: int
    installment_total: int
    charge_now: bool


@dataclass(frozen=True, slots=True)
class PaymentRegenerationDecision:
    due_date: date
    installment_number: int
    installment_total: int
    note: str


def build_payment_schedule_plan(
    *,
    due_date: date,
    amount: Decimal,
    billing_strategy: str,
    installment_total: int,
    recurrence_cycles: int,
    billing_cycle: str,
    confirm_payment_now: bool,
) -> list[PlannedPayment]:
    normalized_amount = Decimal(amount)

    if billing_strategy == 'installments':
        total = max(installment_total, 1)
        installment_amount = (normalized_amount / total).quantize(Decimal('0.01'))
        running_total = Decimal('0.00')
        planned_payments: list[PlannedPayment] = []
        for index in range(1, total + 1):
            current_amount = installment_amount if index < total else normalized_amount - running_total
            running_total += current_amount
            planned_payments.append(
                PlannedPayment(
                    due_date=advance_due_date(
                        start_date=due_date,
                        step=index - 1,
                        billing_cycle=billing_cycle,
                    ),
                    amount=current_amount,
                    installment_number=index,
                    installment_total=total,
                    charge_now=confirm_payment_now and index == 1,
                )
            )
        return planned_payments

    if billing_strategy == 'recurring':
        total = max(recurrence_cycles, 1)
        return [
            PlannedPayment(
                due_date=advance_due_date(
                    start_date=due_date,
                    step=index - 1,
                    billing_cycle=billing_cycle,
                ),
                amount=normalized_amount,
                installment_number=index,
                installment_total=total,
                charge_now=confirm_payment_now and index == 1,
            )
            for index in range(1, total + 1)
        ]

    return [
        PlannedPayment(
            due_date=due_date,
            amount=normalized_amount,
            installment_number=1,
            installment_total=1,
            charge_now=confirm_payment_now,
        )
    ]


def build_payment_regeneration_decision(
    *,
    current_due_date: date,
    current_installment_number: int,
    current_installment_total: int,
    billing_cycle: str,
) -> PaymentRegenerationDecision:
    next_installment_number = current_installment_number + 1
    return PaymentRegenerationDecision(
        due_date=advance_due_date(
            start_date=current_due_date,
            step=1,
            billing_cycle=billing_cycle,
        ),
        installment_number=next_installment_number,
        installment_total=max(current_installment_total, next_installment_number),
        note='Cobranca regenerada pela tela do aluno.',
    )


__all__ = [
    'PaymentRegenerationDecision',
    'PlannedPayment',
    'advance_due_date',
    'build_payment_regeneration_decision',
    'build_payment_schedule_plan',
    'shift_month',
]