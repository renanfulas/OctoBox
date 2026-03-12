"""
ARQUIVO: regras puras de agenda financeira do aluno.

POR QUE ELE EXISTE:
- Centraliza a logica de avanço de vencimento sem depender de ORM ou timezone do Django.

O QUE ESTE ARQUIVO FAZ:
1. Avança meses preservando o primeiro dia do ciclo.
2. Calcula o próximo vencimento conforme o ciclo de cobrança.

PONTOS CRITICOS:
- Essas regras afetam parcelamento, recorrencia e regeneracao de cobrança.
"""

from datetime import date, timedelta


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


__all__ = ['advance_due_date', 'shift_month']