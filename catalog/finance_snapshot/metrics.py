"""
ARQUIVO: indicadores e pulso executivo do snapshot financeiro.

POR QUE ELE EXISTE:
- mantem metricas financeiras e resumo executivo separados da montagem de querysets no app real catalog.

O QUE ESTE ARQUIVO FAZ:
1. formata valores monetarios para notas de apoio.
2. monta os indicadores da central financeira.
3. extrai o pulso executivo resumido.

PONTOS CRITICOS:
- mudancas aqui afetam leitura gerencial e textos das metricas.
"""

from collections import OrderedDict
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from finance.models import EnrollmentStatus, Payment, PaymentStatus


def _format_currency_br(value):
    normalized = (value or Decimal('0.00')).quantize(Decimal('0.01'))
    return f'{normalized:.2f}'.replace('.', ',')


def build_finance_metrics(payments, enrollments):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    previous_month_end = month_start - timezone.timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    revenue_this_month = payments.filter(
        status=PaymentStatus.PAID,
        due_date__gte=month_start,
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
    revenue_previous_month = Payment.objects.filter(
        status=PaymentStatus.PAID,
        due_date__gte=previous_month_start,
        due_date__lte=previous_month_end,
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
    open_revenue = payments.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
    paid_count = payments.filter(status=PaymentStatus.PAID, due_date__gte=month_start).count()
    active_growth = enrollments.filter(
        status=EnrollmentStatus.ACTIVE,
        start_date__gte=month_start,
    ).count()
    cancellations = enrollments.filter(
        status=EnrollmentStatus.CANCELED,
        updated_at__date__gte=month_start,
    ).count()
    overdue_students = payments.filter(status=PaymentStatus.OVERDUE).values('student_id').distinct().count()

    return OrderedDict(
        [
            (
                'Receita recebida no mes',
                {
                    'value': revenue_this_month,
                    'note': f'No mes anterior, entraram R$ {_format_currency_br(revenue_previous_month)}.',
                    'is_currency': True,
                },
            ),
            (
                'Receita que ainda nao entrou',
                {
                    'value': open_revenue,
                    'note': 'Mostra o volume que ainda depende de cobranca ou regularizacao.',
                    'is_currency': True,
                },
            ),
            (
                'Novos contratos no mes',
                {
                    'value': active_growth,
                    'note': 'Entradas reais que reforcaram a carteira neste mes.',
                    'is_currency': False,
                },
            ),
            (
                'Cancelamentos no mes',
                {
                    'value': cancellations,
                    'note': 'Saidas que impactam recorrencia e pedem leitura de retencao.',
                    'is_currency': False,
                },
            ),
            (
                'Ticket medio recebido',
                {
                    'value': revenue_this_month / paid_count if paid_count else Decimal('0.00'),
                    'note': 'Quanto a operacao efetivamente trouxe por pagamento recebido.',
                    'is_currency': True,
                },
            ),
            (
                'Alunos com atraso ativo',
                {
                    'value': overdue_students,
                    'note': 'Quantidade de pessoas que ja pedem acao de cobranca e cuidado comercial.',
                    'is_currency': False,
                },
            ),
        ]
    )


def build_finance_pulse(finance_metrics):
    return {
        'received': finance_metrics['Receita recebida no mes']['value'],
        'open': finance_metrics['Receita que ainda nao entrou']['value'],
        'overdue_students': finance_metrics['Alunos com atraso ativo']['value'],
        'ticket': finance_metrics['Ticket medio recebido']['value'],
    }


__all__ = ['build_finance_metrics', 'build_finance_pulse']