"""
ARQUIVO: queries do snapshot principal do dashboard.

POR QUE ELE EXISTE:
- Centraliza as leituras e agregacoes do painel principal fora da camada HTTP.

O QUE ESTE ARQUIVO FAZ:
1. Monta metricas do painel.
2. Monta proximas aulas, alertas financeiros e saude da base.
3. Devolve um snapshot unico para a view do dashboard.

PONTOS CRITICOS:
- Mudancas aqui afetam numeros, alertas e desempenho do painel principal.
"""

from django.db.models import Count, Q, Sum
from django.utils import timezone

from finance.models import Payment, PaymentStatus
from operations.models import Attendance, AttendanceStatus, BehaviorNote, ClassSession
from boxcore.session_snapshots import serialize_class_session, sync_runtime_statuses
from students.models import Student, StudentStatus


def build_dashboard_snapshot(*, today, month_start):
    active_students = Student.objects.filter(status=StudentStatus.ACTIVE)
    sessions_today = ClassSession.objects.filter(scheduled_at__date=today)
    overdue_payments = Payment.objects.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        due_date__lt=today,
    )
    monthly_attendance = Attendance.objects.filter(
        session__scheduled_at__date__gte=month_start,
        status__in=[AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT],
    )
    current_time = timezone.localtime()
    upcoming_session_objects = list(
        ClassSession.objects.filter(scheduled_at__date__gte=today)
        .select_related('coach')
        .annotate(occupied_slots=Count('attendances'))
        .order_by('scheduled_at')[:5]
    )
    sync_runtime_statuses(upcoming_session_objects, now=current_time)

    metrics = {
        'active_students': active_students.count(),
        'sessions_today': sessions_today.count(),
        'overdue_payments': overdue_payments.count(),
        'attendance_this_month': monthly_attendance.count(),
        'monthly_revenue_paid': Payment.objects.filter(
            status=PaymentStatus.PAID,
            due_date__gte=month_start,
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'occurrences_this_month': BehaviorNote.objects.filter(
            happened_at__date__gte=month_start,
        ).count(),
    }

    return {
        'metrics': metrics,
        'hero_stats': [
            {'label': 'Base ativa', 'value': metrics['active_students']},
            {'label': 'Aulas hoje', 'value': metrics['sessions_today']},
            {'label': 'Atrasos', 'value': metrics['overdue_payments']},
            {'label': 'Receita', 'value': 'R$ %s' % metrics['monthly_revenue_paid']},
        ],
        'metric_cards': [
            {'card_class': 'dashboard-kpi-card kpi-amber', 'eyebrow': 'Alunos ativos', 'display_value': metrics['active_students'], 'note': 'Base principal para check-in, receita recorrente e retenção.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-blue', 'eyebrow': 'Aulas hoje', 'display_value': metrics['sessions_today'], 'note': 'Agenda operacional do dia e pressão imediata na equipe.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-red', 'eyebrow': 'Pagamentos atrasados', 'display_value': metrics['overdue_payments'], 'note': 'Prioridade para ação da secretaria, cobrança e retenção.', 'footer_pill_label': 'Ação imediata' if metrics['overdue_payments'] > 0 else 'Sob controle', 'footer_pill_class': 'warning' if metrics['overdue_payments'] > 0 else 'success'},
            {'card_class': 'dashboard-kpi-card kpi-green', 'eyebrow': 'Presenças no mês', 'display_value': metrics['attendance_this_month'], 'note': 'Volume real de comparecimentos que sustenta a leitura de engajamento.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-amber', 'eyebrow': 'Receita recebida no mês', 'display_value': 'R$ %s' % metrics['monthly_revenue_paid'], 'note': 'Somatório dos pagamentos marcados como pagos no recorte atual.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-slate', 'eyebrow': 'Ocorrências no mês', 'display_value': metrics['occurrences_this_month'], 'note': 'Sinal de acompanhamento técnico e comportamental ao longo da base.', 'show_accent_bar': True},
        ],
        'upcoming_sessions': [
            serialize_class_session(session, now=current_time)
            for session in upcoming_session_objects
        ],
        'payment_alerts': overdue_payments.select_related('student').order_by('due_date')[:5],
        'student_health': (
            Student.objects.annotate(
                total_attendances=Count(
                    'attendances',
                    filter=Q(attendances__status__in=[AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT]),
                ),
                total_absences=Count(
                    'attendances',
                    filter=Q(attendances__status=AttendanceStatus.ABSENT),
                ),
            )
            .order_by('-total_absences', '-total_attendances', 'full_name')[:8]
        ),
    }