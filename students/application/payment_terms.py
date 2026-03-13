"""
ARQUIVO: fachada de compatibilidade para regras puras de agenda financeira do aluno.

POR QUE ELE EXISTE:
- Preserva imports historicos enquanto a politica financeira migra para a camada de dominio explicita.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta calculo de vencimento e planejamento puro de cobrancas.

PONTOS CRITICOS:
- Nova regra deve nascer em students.domain, nao aqui.
"""

from students.domain import (
    PaymentRegenerationDecision,
    PlannedPayment,
    advance_due_date,
    build_payment_regeneration_decision,
    build_payment_schedule_plan,
    shift_month,
)

__all__ = [
    'PaymentRegenerationDecision',
    'PlannedPayment',
    'advance_due_date',
    'build_payment_regeneration_decision',
    'build_payment_schedule_plan',
    'shift_month',
]