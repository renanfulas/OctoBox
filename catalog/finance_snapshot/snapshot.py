"""
ARQUIVO: montagem final do snapshot financeiro.

POR QUE ELE EXISTE:
- orquestra as partes menores do financeiro em um snapshot unico para tela e exportacao no app real catalog.

O QUE ESTE ARQUIVO FAZ:
1. resolve o formulario de filtros.
2. monta metricas, portfolio, mix e comparativos.
3. devolve alertas e movimentos recentes.

PONTOS CRITICOS:
- a estrutura de saida precisa permanecer estavel para templates e relatorios.
"""

from finance.models import FinanceFollowUp, PaymentStatus
from finance.follow_up_tracker import sync_finance_follow_up_suggestions

from ..forms import FinanceFilterForm
from .base import build_finance_base
from .churn_foundation import build_financial_churn_foundation
from .comparison import build_comparison_peaks, build_monthly_comparison
from .follow_up_analytics import (
    build_best_action_by_timing_map,
    build_best_prediction_window_by_action_map,
    build_contextual_recommendation_map,
    build_finance_follow_up_analytics,
    build_recommendation_historical_score_map,
    build_recommendation_timing_lookup_map,
    build_turn_priority_tension_context_map,
    build_turn_recommendation,
    build_timing_recommendation_override_map,
)
from .metrics import build_finance_interactive_kpis, build_finance_metrics, build_finance_priority_context, build_finance_pulse
from .portfolio import build_plan_portfolio
from django.utils import timezone


def build_finance_flow_bridge(*, priority_context, operational_queue, financial_alerts):
    assisted_count = len(operational_queue or [])
    queue_count = len(financial_alerts or [])
    dominant_key = priority_context['dominant_key']

    if dominant_key == 'queue':
        if assisted_count > 0:
            return {
                'eyebrow': 'Primeiro movimento',
                'title': 'Abra a regua assistida antes de descer para a fila automatica.',
                'copy': f'{assisted_count} caso(s) ja chegam com abordagem sugerida. Resolva essa camada primeiro e deixe a fila de {queue_count} alerta(s) para o que realmente sobrar de pressao.',
                'href': '#finance-priority-board',
                'href_label': 'Abrir regua ativa',
                'data_action': 'open-tab-finance-queue',
                'entry_surface': 'priority-rail',
                'entry_reason': 'Existe abordagem semiassistida pronta antes da fila automatica.',
                'secondary_surface': 'queue-board',
            }
        return {
            'eyebrow': 'Primeiro movimento',
            'title': 'A fila automatica virou a primeira porta desta leitura.',
            'copy': f'Nao ha regua assistida aberta agora. Entre direto na fila com {queue_count} alerta(s) e proteja o caixa antes de abrir carteira ou filtros.',
            'href': '#finance-queue-board',
            'href_label': 'Abrir fila financeira',
            'data_action': 'open-tab-finance-queue',
            'entry_surface': 'queue-board',
            'entry_reason': 'A pressao de caixa pede leitura direta da fila automatica.',
            'secondary_surface': 'portfolio-board',
        }
    if dominant_key == 'movements':
        return {
            'eyebrow': 'Primeiro movimento',
            'title': 'Leia o caixa realizado e use a tendencia para escolher o proximo mergulho.',
            'copy': 'Comece pelo raio-X financeiro, confirme movimentos recentes e so depois desca para fila ou carteira se o recorte pedir.',
            'href': '#finance-movements-board',
            'href_label': 'Abrir raio-X financeiro',
            'data_action': 'open-tab-finance-movements',
            'entry_surface': 'movements-board',
            'entry_reason': 'Sem pressao dominante na fila, o caixa realizado explica melhor o recorte.',
            'secondary_surface': 'queue-board',
        }
    return {
        'eyebrow': 'Primeiro movimento',
        'title': 'Comece pela carteira e deixe a fila para a segunda leitura.',
        'copy': 'Sem pressao dominante na fila ou no caixa, portfolio e mix explicam melhor o momento antes de abrir filtros ou cobrancas.',
        'href': '#finance-portfolio-board',
        'href_label': 'Abrir carteira ativa',
        'data_action': 'open-tab-finance-portfolio',
        'entry_surface': 'portfolio-board',
        'entry_reason': 'Carteira e mix explicam mais do que movimentos curtos neste recorte.',
        'secondary_surface': 'queue-board',
    }


def build_finance_snapshot(params=None, *, operational_queue=None, persist_follow_ups=False):
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
    finance_pulse = build_finance_pulse(finance_metrics)
    finance_priority_context = build_finance_priority_context(finance_metrics)
    queue_focus = ''
    if filter_form.is_valid():
        queue_focus = filter_form.cleaned_data.get('queue_focus') or ''
    students = [
        payment.student
        for payment in payments.select_related('student')
    ]
    students_by_id = {student.id: student for student in students}
    for enrollment in enrollments.select_related('student'):
        students_by_id.setdefault(enrollment.student_id, enrollment.student)
    financial_alerts = payments.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
    ).order_by('due_date', 'student__full_name')[:8]
    current_follow_ups = FinanceFollowUp.objects.filter(source_surface='finance_queue')
    historical_follow_up_analytics = build_finance_follow_up_analytics(follow_ups=current_follow_ups)
    turn_recommendation = build_turn_recommendation(historical_follow_up_analytics)
    financial_churn_foundation = build_financial_churn_foundation(
        students=students_by_id.values(),
        payments=payments,
        enrollments=enrollments,
        today=timezone.localdate(),
        queue_focus=queue_focus,
        historical_score_map=build_recommendation_historical_score_map(historical_follow_up_analytics),
        recommendation_timing_map=build_best_action_by_timing_map(historical_follow_up_analytics),
        recommendation_timing_lookup_map=build_recommendation_timing_lookup_map(historical_follow_up_analytics),
        recommendation_override_map=build_timing_recommendation_override_map(historical_follow_up_analytics),
        prediction_window_override_map=build_best_prediction_window_by_action_map(historical_follow_up_analytics),
        contextual_recommendation_map=build_contextual_recommendation_map(historical_follow_up_analytics),
        turn_priority_tension_context_map=build_turn_priority_tension_context_map(historical_follow_up_analytics),
    )
    if persist_follow_ups:
        sync_finance_follow_up_suggestions(
            items=financial_churn_foundation.get('queue_preview') or [],
            turn_recommendation=turn_recommendation,
        )
    finance_follow_up_analytics = build_finance_follow_up_analytics(
        follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
    )

    snapshot = {
        'filter_form': filter_form,
        'payments': payments,
        'enrollments': enrollments,
        'plans': plans,
        'finance_metrics': finance_metrics,
        'finance_pulse': finance_pulse,
        'finance_priority_context': finance_priority_context,
        'interactive_kpis': build_finance_interactive_kpis(finance_metrics, priority_context=finance_priority_context),
        'plan_portfolio': plan_portfolio,
        'monthly_comparison': monthly_comparison,
        'comparison_peaks': build_comparison_peaks(monthly_comparison),
        'financial_alerts': financial_alerts,
        'financial_churn_foundation': financial_churn_foundation,
        'finance_follow_up_analytics': finance_follow_up_analytics,
        'recent_movements': enrollments.order_by('-updated_at', '-created_at')[:8],
    }

    if operational_queue is not None:
        snapshot['finance_flow_bridge'] = build_finance_flow_bridge(
            priority_context=finance_priority_context,
            operational_queue=operational_queue,
            financial_alerts=financial_alerts,
        )

    return snapshot


__all__ = ['build_finance_flow_bridge', 'build_finance_snapshot']
