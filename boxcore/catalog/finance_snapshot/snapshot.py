"""
ARQUIVO: montagem final do snapshot financeiro.

POR QUE ELE EXISTE:
- Orquestra as partes menores do financeiro em um snapshot unico para tela e exportacao.

O QUE ESTE ARQUIVO FAZ:
1. Resolve o formulario de filtros.
2. Monta metricas, portfolio, mix e comparativos.
3. Devolve alertas e movimentos recentes.

PONTOS CRITICOS:
- A estrutura de saida precisa permanecer estavel para templates e relatorios.
"""

from boxcore.models import PaymentStatus

from ..forms import FinanceFilterForm
from .base import build_finance_base
from .comparison import build_comparison_peaks, build_monthly_comparison
from .metrics import build_finance_metrics, build_finance_pulse
from .portfolio import build_plan_mix, build_plan_portfolio


def build_finance_snapshot(params=None):
    filter_form = FinanceFilterForm(params or None)
    finance_base = build_finance_base(filter_form)
    payments = finance_base['payments']
    enrollments = finance_base['enrollments']
    plans = finance_base['plans']
    plan_portfolio = list(build_plan_portfolio(plans, payments, enrollments))
    monthly_comparison = build_monthly_comparison(
        finance_base['months'],
        finance_base['selected_plan'],
        finance_base['payment_status'],
        finance_base['payment_method'],
    )
    finance_metrics = build_finance_metrics(payments, enrollments)

    return {
        'filter_form': filter_form,
        'payments': payments,
        'enrollments': enrollments,
        'plans': plans,
        'finance_metrics': finance_metrics,
        'finance_pulse': build_finance_pulse(finance_metrics),
        'plan_portfolio': plan_portfolio,
        'plan_mix': build_plan_mix(plan_portfolio),
        'monthly_comparison': monthly_comparison,
        'comparison_peaks': build_comparison_peaks(monthly_comparison),
        'financial_alerts': payments.filter(
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        ).order_by('due_date', 'student__full_name')[:8],
        'recent_movements': enrollments.order_by('-updated_at', '-created_at')[:8],
    }


__all__ = ['build_finance_snapshot']