"""
ARQUIVO: regra compartilhada de leitura para atraso financeiro.

POR QUE ELE EXISTE:
- Mantem shell, dashboard, financeiro e workspaces lendo a mesma definicao de cobranca em atraso.

O QUE ESTE ARQUIVO FAZ:
1. Define o queryset base de pagamentos atrasados reais.
2. Conta pagamentos e alunos afetados sem depender apenas da persistencia do status OVERDUE.

PONTOS CRITICOS:
- Atraso real aqui significa cobranca nao paga cujo vencimento ja passou.
- Se essa regra divergir entre telas, o produto perde confianca operacional imediatamente.
"""

from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from finance.models import PaymentStatus


def get_overdue_payments_queryset(payments, *, today):
    return payments.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        due_date__lt=today,
    )


def count_overdue_students(payments, *, today):
    return get_overdue_payments_queryset(payments, today=today).values('student_id').distinct().count()


def sum_overdue_amount(payments, *, today):
    return get_overdue_payments_queryset(payments, today=today).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00')),
    )['total']


__all__ = ['count_overdue_students', 'get_overdue_payments_queryset', 'sum_overdue_amount']