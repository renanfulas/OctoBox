"""
ARQUIVO: regras puras das acoes operacionais de communications.

POR QUE ELE EXISTE:
- Tira do adapter Django decisoes de negocio simples, mas recorrentes, do fluxo operacional.

O QUE ESTE ARQUIVO FAZ:
1. Decide quando uma cobranca deve ser tratada como atrasada.

PONTOS CRITICOS:
- Esta camada trabalha apenas com valores simples e enums de negocio ja resolvidos.
"""


def should_mark_payment_overdue(*, action_kind, payment_status, payment_due_date, reference_date):
    return (
        action_kind == 'overdue'
        and payment_status == 'pending'
        and payment_due_date is not None
        and payment_due_date < reference_date
    )


__all__ = ['should_mark_payment_overdue']