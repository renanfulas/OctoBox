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
from .ai import (
    build_best_action_by_timing_map,
    build_best_prediction_window_by_action_map,
    build_contextual_recommendation_map,
    build_financial_churn_foundation,
    build_finance_follow_up_analytics,
    build_recommendation_historical_score_map,
    build_recommendation_timing_lookup_map,
    build_turn_priority_tension_context_map,
    build_turn_recommendation,
    build_timing_recommendation_override_map,
)
from django.utils import timezone
from .hybrid.flow_bridge import build_finance_flow_bridge
from .traditional import (
    build_comparison_peaks,
    build_finance_base,
    build_finance_interactive_kpis,
    build_finance_metrics,
    build_finance_priority_context,
    build_finance_pulse,
    build_finance_trend_foundation,
    build_monthly_comparison,
    build_plan_portfolio,
)


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
    finance_trend_foundation = build_finance_trend_foundation(
        filter_form=filter_form,
        finance_metrics=finance_metrics,
        monthly_comparison=monthly_comparison,
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
        'finance_trend_foundation': finance_trend_foundation,
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
