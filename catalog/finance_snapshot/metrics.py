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

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from finance.models import EnrollmentStatus, Payment, PaymentStatus
from finance.overdue_metrics import count_overdue_students, get_overdue_payments_queryset, sum_overdue_amount


def _format_currency_br(value):
    normalized = (value or Decimal('0.00')).quantize(Decimal('0.01'))
    return f'{normalized:.2f}'.replace('.', ',')


def build_finance_metrics(payments, enrollments):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    previous_month_end = month_start - timezone.timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    # 🚀 Agregacao atomica para evitar multiplas queries (Epic 8 Performance)
    # Reduz de ~6 queries para 1 única busca consolidada.
    summary = payments.aggregate(
        revenue_this_month=Coalesce(
            Sum('amount', filter=Q(status=PaymentStatus.PAID, due_date__gte=month_start)),
            Decimal('0.00'),
        ),
        open_revenue=Coalesce(
            Sum('amount', filter=Q(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE])),
            Decimal('0.00'),
        ),
        paid_count=Count('id', filter=Q(status=PaymentStatus.PAID, due_date__gte=month_start)),
    )

    revenue_this_month = summary['revenue_this_month']
    open_revenue = summary['open_revenue']
    paid_count = summary['paid_count']

    # Consultas auxiliares de contexto temporal (necessarias por serem QuerySets distintos ou base temporal diferente)
    revenue_previous_month = Payment.objects.filter(
        status=PaymentStatus.PAID,
        due_date__gte=previous_month_start,
        due_date__lte=previous_month_end,
    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']

    active_growth = enrollments.filter(status=EnrollmentStatus.ACTIVE, start_date__gte=month_start).count()
    cancellations = enrollments.filter(status=EnrollmentStatus.CANCELED, updated_at__date__gte=month_start).count()
    
    overdue_students = count_overdue_students(payments, today=today)
    overdue_payments = get_overdue_payments_queryset(payments, today=today)
    overdue_amount = sum_overdue_amount(payments, today=today)

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
                    'submetric': {
                        'label': 'Valor vencido',
                        'value': f'R$ {_format_currency_br(overdue_amount)}',
                    },
                    'note': f'{overdue_payments.count()} cobranca(s) ja passaram do vencimento e pedem acao de cobranca e cuidado comercial.',
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


def build_finance_interactive_kpis(finance_metrics):
    return [
        {
            'eyebrow': 'Raio-X Financeiro',
            'display_value': f"R$ {_format_currency_br(finance_metrics['Receita recebida no mes']['value'])}",
            'note': 'Movimentos, entradas, saidas e graficos de tendencia financeira.',
            'data_action': 'open-tab-finance-movements',
            'card_class': 'kpi-emerald',
        },
        {
            'eyebrow': 'Handoff de Cobranca',
            'display_value': f"R$ {_format_currency_br(finance_metrics['Receita que ainda nao entrou']['value'])}",
            'note': 'Fila automatica e regua ativa contra a inadimplencia e atrasos.',
            'data_action': 'open-tab-finance-queue',
            'card_class': 'kpi-red' if finance_metrics['Alunos com atraso ativo']['value'] > 0 else 'kpi-blue',
        },
        {
            'eyebrow': 'Motor de Carteira',
            'display_value': str(finance_metrics['Novos contratos no mes']['value']),
            'note': 'Portfolio de planos, mix de base e concentracao de receita.',
            'data_action': 'open-tab-finance-portfolio',
            'card_class': 'kpi-slate',
        },
        {
            'eyebrow': 'Filtros & Exportacao',
            'display_value': 'Recortes',
            'note': 'Acesse os controles globais para isolar status, datas e planilhas.',
            'data_action': 'open-tab-finance-filters',
            'card_class': 'kpi-cyan',
        },
    ]


__all__ = ['build_finance_metrics', 'build_finance_pulse', 'build_finance_interactive_kpis']