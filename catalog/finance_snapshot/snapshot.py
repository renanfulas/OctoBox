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
- `filter_form`, `payments`, `enrollments` e `plans` continuam server-only por enquanto.
- listas de leitura para UI e transporte devem preferir estruturas JSON-safe em `transport_payload`.
"""

from time import perf_counter

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


def _build_student_financial_overview_url(student_id):
    if not student_id:
        return ''
    # Evita o custo frio do reverse repetido para uma rota estavel e altamente serializada.
    return f'/alunos/{student_id}/editar/#student-financial-overview'


def _serialize_financial_alert(payment):
    enrollment = getattr(payment, 'enrollment', None)
    student = getattr(payment, 'student', None)
    return {
        'id': payment.id,
        'student_id': getattr(student, 'id', None),
        'student_full_name': getattr(student, 'full_name', 'Aluno'),
        'student_url': _build_student_financial_overview_url(getattr(student, 'id', None)),
        'plan_name': enrollment.plan.name if enrollment and getattr(enrollment, 'plan', None) else 'Sem vinculo de plano',
        'due_date': payment.due_date,
        'amount': payment.amount,
        'status': payment.status,
    }


def _serialize_recent_movement(enrollment):
    student = getattr(enrollment, 'student', None)
    plan = getattr(enrollment, 'plan', None)
    return {
        'id': enrollment.id,
        'student_id': getattr(student, 'id', None),
        'student_full_name': getattr(student, 'full_name', 'Aluno'),
        'plan_name': getattr(plan, 'name', 'Plano'),
        'status': enrollment.status,
        'start_date': enrollment.start_date,
        'updated_at': enrollment.updated_at,
        'student_url': _build_student_financial_overview_url(getattr(student, 'id', None)),
    }


def _build_finance_transport_payload(*, financial_alerts, recent_movements):
    return {
        'financial_alerts': [_serialize_financial_alert(payment) for payment in financial_alerts],
        'recent_movements': [_serialize_recent_movement(enrollment) for enrollment in recent_movements],
    }


def build_finance_snapshot(params=None, *, operational_queue=None, persist_follow_ups=False):
    started_at = perf_counter()
    performance_timing = {}

    filter_form_started_at = perf_counter()
    filter_form = FinanceFilterForm(params or None)
    performance_timing['filter_form_ms'] = round((perf_counter() - filter_form_started_at) * 1000, 2)

    finance_base_started_at = perf_counter()
    finance_base = build_finance_base(filter_form)
    performance_timing['base_snapshot_ms'] = round((perf_counter() - finance_base_started_at) * 1000, 2)
    payments = finance_base['payments']
    enrollments = finance_base['enrollments']
    plans = finance_base['plans']

    plan_portfolio_started_at = perf_counter()
    plan_portfolio = list(build_plan_portfolio(plans, payments, enrollments))
    performance_timing['plan_portfolio_ms'] = round((perf_counter() - plan_portfolio_started_at) * 1000, 2)

    monthly_comparison_started_at = perf_counter()
    monthly_comparison = build_monthly_comparison(
        finance_base['months'],
        finance_base['selected_plan'],
        finance_base['payment_status'],
        finance_base['payment_method'],
    )
    performance_timing['monthly_comparison_ms'] = round((perf_counter() - monthly_comparison_started_at) * 1000, 2)

    finance_metrics_started_at = perf_counter()
    finance_metrics = build_finance_metrics(payments, enrollments)
    performance_timing['finance_metrics_ms'] = round((perf_counter() - finance_metrics_started_at) * 1000, 2)
    finance_pulse = build_finance_pulse(finance_metrics)
    finance_priority_context = build_finance_priority_context(finance_metrics)
    queue_focus = ''
    if filter_form.is_valid():
        queue_focus = filter_form.cleaned_data.get('queue_focus') or ''

    student_scope_started_at = perf_counter()
    students = [
        payment.student
        for payment in payments.select_related('student')
    ]
    students_by_id = {student.id: student for student in students}
    for enrollment in enrollments.select_related('student'):
        students_by_id.setdefault(enrollment.student_id, enrollment.student)
    performance_timing['student_scope_ms'] = round((perf_counter() - student_scope_started_at) * 1000, 2)

    alert_rows_started_at = perf_counter()
    financial_alerts = payments.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
    ).order_by('due_date', 'student__full_name')[:8]
    performance_timing['financial_alerts_ms'] = round((perf_counter() - alert_rows_started_at) * 1000, 2)

    follow_up_analytics_started_at = perf_counter()
    current_follow_ups = FinanceFollowUp.objects.filter(source_surface='finance_queue')
    historical_follow_up_analytics = build_finance_follow_up_analytics(follow_ups=current_follow_ups)
    turn_recommendation = build_turn_recommendation(historical_follow_up_analytics)
    performance_timing['follow_up_analytics_ms'] = round((perf_counter() - follow_up_analytics_started_at) * 1000, 2)

    churn_foundation_started_at = perf_counter()
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
    performance_timing['financial_churn_foundation_ms'] = round((perf_counter() - churn_foundation_started_at) * 1000, 2)
    if persist_follow_ups:
        sync_finance_follow_up_suggestions(
            items=financial_churn_foundation.get('queue_preview') or [],
            turn_recommendation=turn_recommendation,
        )

    refresh_follow_up_started_at = perf_counter()
    if persist_follow_ups:
        finance_follow_up_analytics = build_finance_follow_up_analytics(
            follow_ups=FinanceFollowUp.objects.filter(source_surface='finance_queue')
        )
    else:
        finance_follow_up_analytics = historical_follow_up_analytics
    performance_timing['follow_up_refresh_ms'] = round((perf_counter() - refresh_follow_up_started_at) * 1000, 2)

    trend_foundation_started_at = perf_counter()
    finance_trend_foundation = build_finance_trend_foundation(
        filter_form=filter_form,
        finance_metrics=finance_metrics,
        monthly_comparison=monthly_comparison,
    )
    performance_timing['trend_foundation_ms'] = round((perf_counter() - trend_foundation_started_at) * 1000, 2)

    recent_movements_started_at = perf_counter()
    recent_movements = list(enrollments.order_by('-updated_at', '-created_at')[:8])
    performance_timing['recent_movements_ms'] = round((perf_counter() - recent_movements_started_at) * 1000, 2)

    transport_payload_started_at = perf_counter()
    transport_payload = _build_finance_transport_payload(
        financial_alerts=financial_alerts,
        recent_movements=recent_movements,
    )
    performance_timing['transport_payload_ms'] = round((perf_counter() - transport_payload_started_at) * 1000, 2)

    snapshot = {
        'filter_form': filter_form,
        'payments': payments,
        'enrollments': enrollments,
        'plans': plans,
        'finance_metrics': finance_metrics,
        'finance_pulse': finance_pulse,
        'finance_priority_context': finance_priority_context,
        'interactive_kpis': build_finance_interactive_kpis(
            finance_metrics,
            priority_context=finance_priority_context,
            plan_portfolio=plan_portfolio,
        ),
        'plan_portfolio': plan_portfolio,
        'monthly_comparison': monthly_comparison,
        'comparison_peaks': build_comparison_peaks(monthly_comparison),
        'financial_alerts': financial_alerts,
        'financial_churn_foundation': financial_churn_foundation,
        'finance_follow_up_analytics': finance_follow_up_analytics,
        'finance_trend_foundation': finance_trend_foundation,
        'recent_movements': recent_movements,
        'transport_payload': transport_payload,
        'performance_timing': performance_timing,
    }

    if operational_queue is not None:
        flow_bridge_started_at = perf_counter()
        snapshot['finance_flow_bridge'] = build_finance_flow_bridge(
            priority_context=finance_priority_context,
            operational_queue=operational_queue,
            financial_alerts=financial_alerts,
        )
        performance_timing['flow_bridge_ms'] = round((perf_counter() - flow_bridge_started_at) * 1000, 2)

    performance_timing['snapshot_total_ms'] = round((perf_counter() - started_at) * 1000, 2)

    return snapshot


__all__ = ['build_finance_flow_bridge', 'build_finance_snapshot']
