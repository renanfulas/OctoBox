"""
ARQUIVO: queries do snapshot principal do dashboard.

POR QUE ELE EXISTE:
- centraliza as leituras e agregacoes do painel principal fora da camada HTTP no app real dashboard.

O QUE ESTE ARQUIVO FAZ:
1. monta metricas do painel.
2. monta proximas aulas, alertas financeiros e saude da base.
3. devolve um snapshot unico para a view do dashboard.

PONTOS CRITICOS:
- mudancas aqui afetam numeros, alertas e desempenho do painel principal.
"""

from django.db.models import Count, Q, Sum
from django.utils import timezone

from finance.models import Payment, PaymentStatus
from operations.models import Attendance, AttendanceStatus, BehaviorNote, ClassSession
from operations.session_snapshots import serialize_class_session, sync_runtime_statuses
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

    operational_focus = []
    if metrics['overdue_payments'] > 0:
        operational_focus.append(
            {
                'label': 'Cobrança pede ação agora',
                'summary': f"{metrics['overdue_payments']} pagamento(s) já passaram do vencimento e pedem contato antes de virarem evasão.",
                'pill_class': 'warning',
                'href': '/financeiro/',
                'href_label': 'Abrir financeiro',
            }
        )
    else:
        operational_focus.append(
            {
                'label': 'Cobrança está sob controle',
                'summary': 'Nenhum atraso crítico apareceu no recorte de hoje.',
                'pill_class': 'success',
                'href': '/financeiro/',
                'href_label': 'Revisar financeiro',
            }
        )

    if metrics['sessions_today'] > 0:
        operational_focus.append(
            {
                'label': 'Agenda do dia está viva',
                'summary': f"{metrics['sessions_today']} aula(s) pedem leitura rápida de coach, ocupação e recepção.",
                'pill_class': 'info',
                'href': '/grade-aulas/',
                'href_label': 'Ver grade',
            }
        )
    else:
        operational_focus.append(
            {
                'label': 'Agenda do dia está leve',
                'summary': 'Não há aulas previstas hoje, então o foco pode cair mais em base e financeiro.',
                'pill_class': 'accent',
                'href': '/grade-aulas/',
                'href_label': 'Abrir grade',
            }
        )

    if metrics['active_students'] > 0:
        operational_focus.append(
            {
                'label': 'Base ativa exige acompanhamento',
                'summary': f"{metrics['active_students']} aluno(s) sustentam a operação e pedem leitura de presença, risco e retenção.",
                'pill_class': 'accent',
                'href': '/alunos/',
                'href_label': 'Abrir alunos',
            }
        )

    return {
        'metrics': metrics,
        'hero_stats': [
            {'label': 'Base ativa', 'value': metrics['active_students']},
            {'label': 'Aulas hoje', 'value': metrics['sessions_today']},
            {'label': 'Atrasos', 'value': metrics['overdue_payments']},
            {'label': 'Receita', 'value': 'R$ %s' % metrics['monthly_revenue_paid']},
        ],
        'metric_cards': [
            {'card_class': 'dashboard-kpi-card kpi-amber', 'eyebrow': 'Alunos ativos', 'display_value': metrics['active_students'], 'note': 'Base principal para check-in, receita recorrente e retencao.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-blue', 'eyebrow': 'Aulas hoje', 'display_value': metrics['sessions_today'], 'note': 'Agenda operacional do dia e pressao imediata na equipe.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-red', 'eyebrow': 'Pagamentos atrasados', 'display_value': metrics['overdue_payments'], 'note': 'Prioridade para acao da secretaria, cobranca e retencao.', 'footer_pill_label': 'Acao imediata' if metrics['overdue_payments'] > 0 else 'Sob controle', 'footer_pill_class': 'warning' if metrics['overdue_payments'] > 0 else 'success'},
            {'card_class': 'dashboard-kpi-card kpi-green', 'eyebrow': 'Presencas no mes', 'display_value': metrics['attendance_this_month'], 'note': 'Volume real de comparecimentos que sustenta a leitura de engajamento.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-amber', 'eyebrow': 'Receita recebida no mes', 'display_value': 'R$ %s' % metrics['monthly_revenue_paid'], 'note': 'Somatorio dos pagamentos marcados como pagos no recorte atual.', 'show_accent_bar': True},
            {'card_class': 'dashboard-kpi-card kpi-slate', 'eyebrow': 'Ocorrencias no mes', 'display_value': metrics['occurrences_this_month'], 'note': 'Sinal de acompanhamento tecnico e comportamental ao longo da base.', 'show_accent_bar': True},
        ],
        'upcoming_sessions': [
            serialize_class_session(session, now=current_time)
            for session in upcoming_session_objects
        ],
        'payment_alerts': overdue_payments.select_related('student').order_by('due_date')[:5],
        'operational_focus': operational_focus,
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


__all__ = ['build_dashboard_snapshot']