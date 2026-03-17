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

from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from access.roles import ROLE_RECEPTION
from communications.application.message_templates import build_operational_message_body
from communications.models import WhatsAppContact
from finance.models import Payment, PaymentStatus
from onboarding.queries import count_pending_intakes
from finance.overdue_metrics import get_overdue_payments_queryset
from operations.models import Attendance, AttendanceStatus, BehaviorNote, ClassSession
from operations.session_snapshots import serialize_class_session, sync_runtime_statuses
from shared_support.whatsapp_contact_state import build_whatsapp_contact_state
from shared_support.whatsapp_links import build_whatsapp_message_href
from students.models import Student, StudentStatus


def _build_payment_alert_whatsapp_href(payment):
    message = build_operational_message_body(
        action_kind='overdue',
        first_name=payment.student.full_name.split()[0],
        payment_due_date=payment.due_date,
        payment_amount=payment.amount,
    )
    return build_whatsapp_message_href(phone=getattr(payment.student, 'phone', ''), message=message)


def _decorate_payment_alerts(payment_alerts):
    student_ids = [payment.student_id for payment in payment_alerts]
    contacts_by_student_id = {
        contact.linked_student_id: contact
        for contact in WhatsAppContact.objects.filter(linked_student_id__in=student_ids)
    }
    for payment in payment_alerts:
        payment.dashboard_whatsapp_href = _build_payment_alert_whatsapp_href(payment)
        contact_state = build_whatsapp_contact_state(contacts_by_student_id.get(payment.student_id))
        payment.dashboard_whatsapp_last_contact_label = contact_state['whatsapp_last_contact_label']
        payment.dashboard_whatsapp_next_available_label = contact_state['whatsapp_next_available_label']
        payment.dashboard_whatsapp_repeat_blocked = contact_state['whatsapp_repeat_blocked']
        payment.dashboard_requires_whatsapp_followup = bool(
            getattr(payment.student, 'status', '') == StudentStatus.ACTIVE
            and payment.dashboard_whatsapp_href
            and not payment.dashboard_whatsapp_repeat_blocked
        )
    return payment_alerts


def _build_dashboard_payment_alert_snapshot(*, overdue_payments_queryset):
    active_overdue_payments = list(
        overdue_payments_queryset
        .select_related('student')
        .filter(student__status=StudentStatus.ACTIVE)
        .order_by('due_date', 'student__full_name')
    )
    decorated_alerts = _decorate_payment_alerts(active_overdue_payments)
    actionable_alerts = [payment for payment in decorated_alerts if payment.dashboard_requires_whatsapp_followup]
    return {
        'payment_alerts': decorated_alerts[:5],
        'payment_alerts_total_count': len(decorated_alerts),
        'payment_alerts_total_label': f'{len(decorated_alerts)} alerta(s)',
        'actionable_payment_alerts_count': len(actionable_alerts),
        'next_actionable_payment_alert': actionable_alerts[0] if actionable_alerts else None,
    }


def _format_currency(value):
    return f'R$ {value:.2f}'


def _build_delta_badge(current, previous, *, label, formatter=str, semantic='neutral'):
    diff = current - previous
    if diff == 0:
        return {'tone': 'neutral', 'value': 'Mesmo ritmo', 'label': label}

    if diff > 0:
        symbol = '+'
        tone = 'good' if semantic == 'positive' else 'bad' if semantic == 'negative' else 'neutral'
    else:
        symbol = '-'
        tone = 'bad' if semantic == 'positive' else 'good' if semantic == 'negative' else 'neutral'

    return {'tone': tone, 'value': f'{symbol} {formatter(abs(diff))}', 'label': label}


def _format_percent(value):
    return f"{int(round(value))}%"


def _build_dashboard_metric_cards(metrics, *, pending_intakes_count, today_schedule_occupancy_percent):
    occupancy_signal_tone = 'good' if today_schedule_occupancy_percent >= 65 else 'neutral'
    occupancy_signal_value = 'Agenda viva' if today_schedule_occupancy_percent >= 65 else 'Dia leve'
    if today_schedule_occupancy_percent >= 95:
        occupancy_signal_tone = 'bad'
        occupancy_signal_value = 'Quase lotado'

    return [
        {
            'card_class': 'dashboard-kpi-card kpi-amber is-stage',
            'eyebrow': 'Receita realizada',
            'kicker': 'Resultado que entrou no caixa',
            'display_value': _format_currency(metrics['monthly_revenue_paid']),
            'change': _build_delta_badge(metrics['monthly_revenue_paid'], metrics['monthly_revenue_paid_previous'], label='vs mes anterior', formatter=_format_currency, semantic='positive'),
            'note': 'Dinheiro que realmente entrou. E a leitura principal para decidir onde apertar caixa, comercial e retencao.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-red is-panel',
            'eyebrow': 'Cobrancas em atraso',
            'kicker': 'Receita que ja escapou da rotina',
            'display_value': metrics['overdue_payments'],
            'change': _build_delta_badge(metrics['overdue_payments'], metrics['overdue_payments_previous_day'], label='desde ontem', semantic='negative'),
            'note': 'Mostra o tamanho do vazamento direto de caixa que o dono precisa conter primeiro.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-blue is-ribbon',
            'eyebrow': 'Entradas pendentes',
            'kicker': 'Fila comercial que ainda pede dono',
            'display_value': pending_intakes_count,
            'signal': {
                'tone': 'neutral' if pending_intakes_count else 'good',
                'value': 'Responder hoje' if pending_intakes_count else 'Fila limpa',
                'label': 'pipeline comercial',
            },
            'note': 'Mostra o quanto ainda existe de oportunidade em aberto antes da conversa esfriar e virar perda invisivel.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-slate is-ledger',
            'eyebrow': 'Aproveitamento da agenda hoje',
            'kicker': 'Ocupacao real do dia',
            'display_value': _format_percent(today_schedule_occupancy_percent),
            'signal': {
                'tone': occupancy_signal_tone,
                'value': occupancy_signal_value,
                'label': 'ocupacao media',
            },
            'note': 'Ajuda a sentir se a agenda do dia esta enchendo bem ou se existem horas ociosas pedindo ajuste comercial ou operacional.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-green is-rail',
            'eyebrow': 'Presenca no mes',
            'kicker': 'Treino que virou rotina',
            'display_value': metrics['attendance_this_month'],
            'change': _build_delta_badge(metrics['attendance_this_month'], metrics['attendance_previous_month'], label='vs mes anterior', semantic='positive'),
            'note': 'Leitura de engajamento real da base. Sem presenca, a receita recorrente vira apenas cadastro otimista.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-amber is-orbit',
            'eyebrow': 'Comunidade ativa',
            'kicker': 'Carteira que sustenta recorrencia',
            'display_value': metrics['active_students'],
            'signal': {'tone': 'good', 'value': 'Base viva', 'label': 'comunidade ativa'},
            'note': 'Referencia do tamanho real da carteira que sustenta receita, agenda e previsibilidade do box.',
            'hide_footer': True,
        },
    ]
def _decorate_dashboard_sessions(serialized_sessions):
    visible_sessions = [session for session in serialized_sessions if session['status_label'] != 'Finalizada']
    for index, session in enumerate(visible_sessions):
        if session['status_label'] == 'Em andamento':
            session['dashboard_kicker'] = 'Em aula agora'
        elif session['booking_closed']:
            session['dashboard_kicker'] = 'Reservas fechadas'
        elif index == 0:
            session['dashboard_kicker'] = 'Proxima aula'
        elif session['occupancy_percent'] >= 90:
            session['dashboard_kicker'] = 'Turma quase lotada'
        else:
            session['dashboard_kicker'] = 'Em seguida'
    return visible_sessions


def _build_dashboard_glance_summary(*, metrics, role_slug, upcoming_sessions, payment_alert_snapshot):
    finance_href = '/operacao/recepcao/#reception-payment-board' if role_slug == ROLE_RECEPTION else '/financeiro/'
    if payment_alert_snapshot['actionable_payment_alerts_count'] > 0:
        count = payment_alert_snapshot['actionable_payment_alerts_count']
        return {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Prioridade imediata',
            'value': count,
            'indicator': 'Caixa' if role_slug == ROLE_RECEPTION else 'Urgente',
            'copy': (
                f'{count} cobranca(s) com espaco real para contato agora. Vale agir antes da agenda roubar energia.'
                if role_slug != ROLE_RECEPTION else
                f'{count} cobranca(s) cabem na abordagem de balcao neste momento. Vale puxar antes da fila crescer.'
            ),
        }

    if upcoming_sessions:
        primary_session = upcoming_sessions[0]
        starts_at_label = timezone.localtime(primary_session['starts_at']).strftime('%H:%M')
        indicator = primary_session['status_label'] if primary_session['status_label'] == 'Em andamento' else primary_session['occupancy_label']
        copy = (
            f"{primary_session['object'].title} esta rodando agora e pede olho em coach, recepcao e ritmo do turno."
            if primary_session['status_label'] == 'Em andamento' else
            f"{primary_session['object'].title} comeca as {starts_at_label} e ja define o pulso operacional do proximo bloco."
        )
        return {
            'href': '#dashboard-sessions-board',
            'card_class': 'is-sessions',
            'indicator_class': 'is-sessions',
            'kicker': 'Agenda imediata',
            'value': len(upcoming_sessions),
            'indicator': indicator,
            'copy': copy,
        }

    return {
        'href': '/alunos/',
        'card_class': 'is-base',
        'indicator_class': 'is-base',
        'kicker': 'Base em foco',
        'value': metrics['active_students'],
        'indicator': 'Comunidade',
        'copy': 'Sem urgencia financeira e sem aula no radar imediato. O melhor uso do turno e cuidar da base ativa.',
    }

def build_dashboard_snapshot(*, today, month_start, role_slug=''):
    previous_day = today - timedelta(days=1)
    previous_month_end = month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    active_students = Student.objects.filter(status=StudentStatus.ACTIVE)
    sessions_today = ClassSession.objects.filter(scheduled_at__date=today)
    sessions_previous_day = ClassSession.objects.filter(scheduled_at__date=previous_day)
    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    overdue_payments_previous_day = get_overdue_payments_queryset(Payment.objects.all(), today=previous_day)
    monthly_attendance = Attendance.objects.filter(
        session__scheduled_at__date__gte=month_start,
        status__in=[AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT],
    )
    previous_month_attendance = Attendance.objects.filter(
        session__scheduled_at__date__gte=previous_month_start,
        session__scheduled_at__date__lt=month_start,
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
        'sessions_previous_day': sessions_previous_day.count(),
        'overdue_payments': overdue_payments.count(),
        'overdue_payments_previous_day': overdue_payments_previous_day.count(),
        'attendance_this_month': monthly_attendance.count(),
        'attendance_previous_month': previous_month_attendance.count(),
        'monthly_revenue_paid': Payment.objects.filter(
            status=PaymentStatus.PAID,
            due_date__gte=month_start,
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'monthly_revenue_paid_previous': Payment.objects.filter(
            status=PaymentStatus.PAID,
            due_date__gte=previous_month_start,
            due_date__lt=month_start,
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'occurrences_this_month': BehaviorNote.objects.filter(
            happened_at__date__gte=month_start,
        ).count(),
        'occurrences_previous_month': BehaviorNote.objects.filter(
            happened_at__date__gte=previous_month_start,
            happened_at__date__lt=month_start,
        ).count(),
    }

    operational_focus = []
    finance_focus_href = '/operacao/recepcao/#reception-payment-board' if role_slug == ROLE_RECEPTION else '/financeiro/'
    finance_focus_label = 'Abrir fila curta da Recepcao' if role_slug == ROLE_RECEPTION else 'Abrir financeiro'
    finance_review_label = 'Revisar fila curta' if role_slug == ROLE_RECEPTION else 'Revisar financeiro'
    if metrics['overdue_payments'] > 0:
        operational_focus.append(
            {
                'label': 'Caixa curto pede acao agora' if role_slug == ROLE_RECEPTION else 'Cobranca pede acao agora',
                'chip_label': 'Cobrancas' if role_slug != ROLE_RECEPTION else 'Caixa',
                'summary': (
                    f"{metrics['overdue_payments']} pagamento(s) ja passaram do vencimento e podem pedir abordagem de balcao ainda hoje."
                    if role_slug == ROLE_RECEPTION else
                    f"{metrics['overdue_payments']} pagamento(s) ja passaram do vencimento e pedem contato antes de virarem evasao."
                ),
                'pill_class': 'warning',
                'href': finance_focus_href,
                'href_label': finance_focus_label,
            }
        )
    else:
        operational_focus.append(
            {
                'label': 'Caixa curto esta sob controle' if role_slug == ROLE_RECEPTION else 'Cobranca esta sob controle',
                'chip_label': 'Cobrancas' if role_slug != ROLE_RECEPTION else 'Caixa',
                'summary': 'Nenhum atraso critico apareceu no recorte de hoje.' if role_slug != ROLE_RECEPTION else 'Nenhuma cobranca curta critica apareceu no recorte de hoje.',
                'pill_class': 'success',
                'href': finance_focus_href,
                'href_label': finance_review_label,
            }
        )

    if metrics['sessions_today'] > 0:
        operational_focus.append(
            {
                'label': 'Agenda do dia esta viva',
                'chip_label': 'Aulas',
                'summary': f"{metrics['sessions_today']} aula(s) pedem leitura rapida de coach, ocupacao e recepcao.",
                'pill_class': 'info',
                'href': '/grade-aulas/',
                'href_label': 'Ver grade',
            }
        )
    else:
        operational_focus.append(
            {
                'label': 'Agenda do dia esta leve',
                'chip_label': 'Aulas',
                'summary': 'Nao ha aulas previstas hoje, entao o foco pode cair mais em base e financeiro.',
                'pill_class': 'accent',
                'href': '/grade-aulas/',
                'href_label': 'Abrir aulas',
            }
        )

    if metrics['active_students'] > 0:
        operational_focus.append(
            {
                'label': 'Base ativa exige acompanhamento',
                'chip_label': 'Base',
                'summary': (
                    f"{metrics['active_students']} aluno(s) sustentam a Recepcao e pedem leitura de ficha, risco e proxima abordagem."
                    if role_slug == ROLE_RECEPTION else
                    f"{metrics['active_students']} aluno(s) sustentam a operacao e pedem leitura de presenca, risco e retencao."
                ),
                'pill_class': 'accent',
                'href': '/alunos/',
                'href_label': 'Abrir alunos',
            }
        )

    payment_alert_snapshot = _build_dashboard_payment_alert_snapshot(overdue_payments_queryset=overdue_payments)
    serialized_sessions = [
        serialize_class_session(session, now=current_time)
        for session in upcoming_session_objects
    ]
    upcoming_sessions = _decorate_dashboard_sessions(serialized_sessions)
    pending_intakes_count = count_pending_intakes()
    today_sessions_with_load = sessions_today.annotate(occupied_slots=Count('attendances'))
    today_schedule_capacity = sum(session.capacity for session in today_sessions_with_load)
    today_schedule_occupied = sum(session.occupied_slots for session in today_sessions_with_load)
    today_schedule_occupancy_percent = (
        (today_schedule_occupied / today_schedule_capacity) * 100
        if today_schedule_capacity else 0
    )
    student_health_queryset = Student.objects.annotate(
        total_attendances=Count(
            'attendances',
            filter=Q(attendances__status__in=[AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT]),
        ),
        total_absences=Count(
            'attendances',
            filter=Q(attendances__status=AttendanceStatus.ABSENT),
        ),
    )
    students_at_risk_count = student_health_queryset.filter(total_absences__gte=1).count()
    student_health = student_health_queryset.order_by('-total_absences', '-total_attendances', 'full_name')[:8]

    return {
        'metrics': metrics,
        'hero_stats': [
            {'label': 'Comunidade ativa', 'value': metrics['active_students']},
            {'label': 'Turmas hoje', 'value': metrics['sessions_today']},
            {'label': 'Atrasos', 'value': metrics['overdue_payments']},
            {'label': 'Receita rodada', 'value': _format_currency(metrics['monthly_revenue_paid'])},
        ],
        'metric_cards': _build_dashboard_metric_cards(
            metrics,
            pending_intakes_count=pending_intakes_count,
            today_schedule_occupancy_percent=today_schedule_occupancy_percent,
        ),
        'glance_summary': _build_dashboard_glance_summary(
            metrics=metrics,
            role_slug=role_slug,
            upcoming_sessions=upcoming_sessions,
            payment_alert_snapshot=payment_alert_snapshot,
        ),
        'upcoming_sessions': upcoming_sessions,
        'payment_alerts': payment_alert_snapshot['payment_alerts'],
        'payment_alerts_total_count': payment_alert_snapshot['payment_alerts_total_count'],
        'payment_alerts_total_label': payment_alert_snapshot['payment_alerts_total_label'],
        'actionable_payment_alerts_count': payment_alert_snapshot['actionable_payment_alerts_count'],
        'next_actionable_payment_alert': payment_alert_snapshot['next_actionable_payment_alert'],
        'operational_focus': operational_focus,
        'student_health': student_health,
    }


__all__ = ['build_dashboard_snapshot']









