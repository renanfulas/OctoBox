"""
ARQUIVO: metricas canonicas da camada tradicional do snapshot financeiro.
"""

from collections import OrderedDict
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from finance.models import EnrollmentStatus, PaymentStatus
from shared_support.kpi_icons import build_kpi_icon


def _format_currency_br(value):
    normalized = (value or Decimal('0.00')).quantize(Decimal('0.01'))
    return f'{normalized:.2f}'.replace('.', ',')


def _finance_kpi_icon(name):
    icon_map = {
        'movements': 'trend',
        'queue': 'queue',
        'portfolio': 'portfolio',
        'filters': 'filters',
    }
    return build_kpi_icon(icon_map.get(name, ''))


def build_finance_metrics(payments, enrollments):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    previous_month_end = month_start - timezone.timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    payment_summary = payments.aggregate(
        revenue_this_month=Coalesce(
            Sum('amount', filter=Q(status=PaymentStatus.PAID, due_date__gte=month_start)),
            Decimal('0.00'),
        ),
        open_revenue=Coalesce(
            Sum('amount', filter=Q(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE])),
            Decimal('0.00'),
        ),
        paid_count=Count('id', filter=Q(status=PaymentStatus.PAID, due_date__gte=month_start)),
        revenue_previous_month=Coalesce(
            Sum(
                'amount',
                filter=Q(
                    status=PaymentStatus.PAID,
                    due_date__gte=previous_month_start,
                    due_date__lte=previous_month_end,
                ),
            ),
            Decimal('0.00'),
        ),
        overdue_students=Count(
            'student_id',
            filter=Q(
                status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
                due_date__lt=today,
            ),
            distinct=True,
        ),
        overdue_payments=Count(
            'id',
            filter=Q(
                status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
                due_date__lt=today,
            ),
        ),
        overdue_amount=Coalesce(
            Sum(
                'amount',
                filter=Q(
                    status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
                    due_date__lt=today,
                ),
            ),
            Decimal('0.00'),
        ),
    )
    enrollment_summary = enrollments.aggregate(
        active_growth=Count(
            'id',
            filter=Q(status=EnrollmentStatus.ACTIVE, start_date__gte=month_start),
        ),
        cancellations=Count(
            'id',
            filter=Q(status=EnrollmentStatus.CANCELED, updated_at__date__gte=month_start),
        ),
    )

    revenue_this_month = payment_summary['revenue_this_month']
    open_revenue = payment_summary['open_revenue']
    paid_count = payment_summary['paid_count']
    revenue_previous_month = payment_summary['revenue_previous_month']
    active_growth = enrollment_summary['active_growth']
    cancellations = enrollment_summary['cancellations']
    overdue_students = payment_summary['overdue_students']
    overdue_payments = payment_summary['overdue_payments']
    overdue_amount = payment_summary['overdue_amount']

    return OrderedDict(
        [
            (
                'Receita recebida no mês',
                {
                    'value': revenue_this_month,
                    'count': paid_count,
                    'note': f'No mês anterior, o caixa realizado fechou em R$ {_format_currency_br(revenue_previous_month)}.',
                    'is_currency': True,
                },
            ),
            (
                'Receita que ainda não entrou',
                {
                    'value': open_revenue,
                    'note': 'Mostra o volume que ainda depende de cobrança, acordo ou regularização.',
                    'is_currency': True,
                },
            ),
            (
                'Novos contratos no mês',
                {
                    'value': active_growth,
                    'note': 'Novas entradas que reforçaram a carteira neste mês.',
                    'is_currency': False,
                },
            ),
            (
                'Cancelamentos no mês',
                {
                    'value': cancellations,
                    'note': 'Saídas que pressionam a recorrência e pedem leitura de retenção.',
                    'is_currency': False,
                },
            ),
            (
                'Ticket médio recebido',
                {
                    'value': revenue_this_month / paid_count if paid_count else Decimal('0.00'),
                    'note': 'Quanto a operação trouxe, em média, por pagamento efetivamente recebido.',
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
                    'note': f'{overdue_payments} cobrança(s) já passaram do vencimento e pedem follow-up antes de virar evasão.',
                    'is_currency': False,
                },
            ),
        ]
    )


def build_finance_pulse(finance_metrics):
    return {
        'received': finance_metrics['Receita recebida no mês']['value'],
        'received_count': finance_metrics['Receita recebida no mês'].get('count', 0),
        'open': finance_metrics['Receita que ainda não entrou']['value'],
        'overdue_students': finance_metrics['Alunos com atraso ativo']['value'],
        'ticket': finance_metrics['Ticket médio recebido']['value'],
    }


def build_finance_priority_context(finance_metrics):
    overdue_students = finance_metrics['Alunos com atraso ativo']['value']
    open_revenue = finance_metrics['Receita que ainda não entrou']['value']
    received_revenue = finance_metrics['Receita recebida no mês']['value']

    if overdue_students > 0:
        return {
            'dominant_key': 'queue',
            'pill_class': 'warning',
            'pill_label': 'Fila dominante',
            'headline': 'A fila de cobrança deve abrir a leitura.',
            'summary': 'Existe atraso ativo na base. Vale entrar em fila e régua antes de expandir carteira ou filtros.',
            'default_action': 'open-tab-finance-queue',
            'default_panel': 'tab-finance-queue',
        }
    if open_revenue > received_revenue and open_revenue > 0:
        return {
            'dominant_key': 'queue',
            'pill_class': 'warning',
            'pill_label': 'Caixa pressionado',
            'headline': 'O dinheiro em aberto já pesa mais que o dinheiro realizado.',
            'summary': 'Mesmo sem atraso dominante, a fila financeira pede abertura antes da leitura de tendência.',
            'default_action': 'open-tab-finance-queue',
            'default_panel': 'tab-finance-queue',
        }
    if received_revenue > 0:
        return {
            'dominant_key': 'movements',
            'pill_class': 'accent',
            'pill_label': 'Caixa em leitura',
            'headline': 'O caixa realizado vira a melhor abertura do recorte.',
            'summary': 'Sem pressão dominante na fila, movimentos e tendência explicam melhor o momento financeiro.',
            'default_action': 'open-tab-finance-movements',
            'default_panel': 'tab-finance-movements',
        }
    return {
        'dominant_key': 'portfolio',
        'pill_class': 'info',
        'pill_label': 'Carteira em foco',
        'headline': 'Sem caixa forte no recorte, a carteira vira o melhor ponto de leitura.',
        'summary': 'Planos, mix e concentração de receita explicam mais do que movimentos curtos neste momento.',
        'default_action': 'open-tab-finance-portfolio',
        'default_panel': 'tab-finance-portfolio',
    }


def build_finance_interactive_kpis(finance_metrics, *, priority_context=None, plan_portfolio=None):
    priority_context = priority_context or build_finance_priority_context(finance_metrics)
    plan_portfolio = plan_portfolio or []
    cards = {
        'movements': {
            'eyebrow': 'Raio-X financeiro',
            'display_value': f"R$ {_format_currency_br(finance_metrics['Receita recebida no mês']['value'])}",
            'icon': _finance_kpi_icon('movements'),
            'note': (
                'Abra caixa, tendência e sinais do período sem sair da central.'
                if priority_context['dominant_key'] != 'movements' else
                'Este é o melhor ponto de abertura agora: o caixa realizado explica o recorte com mais clareza.'
            ),
            'data_action': 'open-tab-finance-movements',
            'card_class': 'kpi-emerald',
            'value_class': 'is-emerald' if finance_metrics['Receita recebida no mês']['value'] > 1 else '',
        },
        'queue': {
            'eyebrow': 'Handoff de cobrança',
            'display_value': f"R$ {_format_currency_br(finance_metrics['Receita que ainda não entrou']['value'])}",
            'icon': _finance_kpi_icon('queue'),
            'note': (
                'Abra a fila assistida para cobrar com prioridade, timing e contexto.'
                if priority_context['dominant_key'] != 'queue' else
                'Esta é a primeira pressão do recorte agora: fila e régua pedem execução antes de aprofundar a carteira.'
            ),
            'data_action': 'open-tab-finance-queue',
            'card_class': 'kpi-red',
            'value_class': 'is-ruby' if finance_metrics['Receita que ainda não entrou']['value'] > 1 else '',
        },
        'portfolio': {
            'eyebrow': 'Motor de carteira',
            'display_value': str(len(plan_portfolio)),
            'icon': _finance_kpi_icon('portfolio'),
            'note': (
                'Leia planos ativos, mix da base e concentração de receita.'
                if priority_context['dominant_key'] != 'portfolio' else
                'Carteira, mix e portfólio explicam melhor o momento do que a fila curta neste recorte.'
            ),
            'data_action': 'open-tab-finance-portfolio',
            'card_class': 'kpi-slate',
        },
        'filters': {
            'eyebrow': 'Filtros e exportação',
            'display_value': 'Recortes',
            'icon': _finance_kpi_icon('filters'),
            'note': 'Ajuste o recorte da leitura para separar janela, plano, status e missão.',
            'data_action': 'open-tab-finance-filters',
            'card_class': 'kpi-ink',
        },
    }

    order = ['movements', 'queue', 'portfolio', 'filters']

    return [cards[key] for key in order]


__all__ = [
    'build_finance_interactive_kpis',
    'build_finance_metrics',
    'build_finance_priority_context',
    'build_finance_pulse',
]
