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
import calendar
from datetime import date

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


def _build_delta_badge(current, previous, *, label, formatter=str, semantic='neutral'):
    # Ensure callers can rely on a numeric representation of the delta
    # 'value' remains the display string, 'value_raw' is always an int/float (or None)
    try:
        diff = (current or 0) - (previous or 0)
    except Exception:
        diff = 0

    # exact same: expose numeric zero but keep human-friendly display
    if diff == 0:
        return {
            'tone': 'neutral',
            'value': 'Mesmo ritmo',
            'value_raw': 0,
            'value_percent': 0,
            'is_small': False,
            'label': label,
        }

    # previous == 0 => first meaningful reading
    if not previous:
        return {
            'tone': 'neutral',
            'value': 'Primeira leitura',
            'value_raw': None,
            'value_percent': None,
            'is_small': False,
            'label': label,
        }

    if diff > 0:
        symbol = '+'
        tone = 'good' if semantic == 'positive' else 'bad' if semantic == 'negative' else 'neutral'
    else:
        symbol = '-'
        tone = 'bad' if semantic == 'positive' else 'good' if semantic == 'negative' else 'neutral'

    # compute percent relative to previous (signed)
    try:
        percent = (diff / float(previous)) * 100
    except Exception:
        percent = None

    is_small = False
    if percent is not None:
        try:
            is_small = abs(percent) <= 10 and tone in ('good', 'bad')
        except Exception:
            is_small = False

    return {
        'tone': tone,
        'value': f'{symbol} {formatter(abs(diff))}',
        'value_raw': diff,
        'value_percent': percent,
        'is_small': is_small,
        'label': label,
    }


def _format_percent(value):
    return f"{int(round(value))}%"


def _format_currency(value):
    try:
        v = float(value or 0)
        # format as BRL: 1.234.567,89
        s = f"{v:,.2f}"
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {s}"
    except Exception:
        return f"R$ {value}"


def _build_dashboard_metric_cards(metrics, *, pending_intakes_count, today_schedule_occupancy_percent):
    occupancy_signal_tone = 'good' if today_schedule_occupancy_percent >= 65 else 'neutral'
    occupancy_signal_value = 'Agenda viva' if today_schedule_occupancy_percent >= 65 else 'Dia leve'
    if today_schedule_occupancy_percent >= 95:
        occupancy_signal_tone = 'bad'
        occupancy_signal_value = 'Quase lotado'

    # Prefer weekly revenue when it's a non-zero reading; otherwise show monthly accumulated
    _weekly = metrics.get('weekly_revenue_paid')
    _weekly_prev = metrics.get('weekly_revenue_paid_previous')
    current_revenue = _weekly if _weekly else metrics['monthly_revenue_paid']
    previous_revenue = _weekly_prev if _weekly_prev else metrics['monthly_revenue_paid_previous']

    return [
        {
            'card_class': 'dashboard-kpi-card kpi-amber is-stage',
            'eyebrow': 'Receita realizada',
            'kicker': 'O que realmente chegou',
            'display_value': _format_currency(current_revenue),
            'change': _build_delta_badge(
                current_revenue,
                previous_revenue,
                label='vs semana anterior',
                formatter=_format_currency,
                semantic='positive',
            ),
            'note': 'Esse e o dinheiro real que entrou. Eu te mostro onde esta indo bem e onde precisa de atencao.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-red is-panel',
            'eyebrow': 'Cobrancas em atraso',
            'kicker': 'Precisa do seu olhar',
            'display_value': metrics['overdue_payments'],
            'change': _build_delta_badge(metrics['overdue_payments'], metrics['overdue_payments_previous_day'], label='desde ontem', semantic='negative'),
            'note': 'Cada cobranca aqui ainda tem chance. Vou te ajudar a priorizar quem abordar primeiro.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-blue is-ribbon',
            'eyebrow': 'Entradas pendentes',
            'kicker': 'Esperando por voce',
            'display_value': pending_intakes_count,
            'signal': {
                'tone': 'neutral' if pending_intakes_count else 'good',
                'value': 'Responder hoje' if pending_intakes_count else 'Fila limpa',
                'label': 'pipeline comercial',
            },
            'note': 'Cada entrada aqui pode ser alguém que está esperando por você mudar a vida dela.\nVamos cuidar antes que esfrie.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-slate is-ledger',
            'eyebrow': 'Aproveitamento da agenda hoje',
            'kicker': 'Pulso do dia',
            'display_value': _format_percent(today_schedule_occupancy_percent),
            'signal': {
                'tone': occupancy_signal_tone,
                'value': occupancy_signal_value,
                'label': 'ocupacao media',
            },
            'note': 'Cuide da lotação para o seu Coach possa entregar uma aula melhor para os alunos.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-green is-rail',
            'eyebrow': 'Presenca no mes',
            'kicker': 'Compromisso que voltou',
            'display_value': metrics['attendance_this_month'],
            'change': _build_delta_badge(metrics['attendance_this_month'], metrics['attendance_previous_month'], label='vs mes anterior', semantic='positive'),
            'note': 'Cada presenca e uma pessoa que escolheu voltar. Voce esta construindo algo que importa.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-emerald is-orbit',
            'eyebrow': 'Comunidade ativa',
            'kicker': 'Sua comunidade viva',
            'display_value': metrics['active_students'],
            'signal': {'tone': 'good', 'value': 'Base viva', 'label': 'comunidade ativa'},
            'note': 'Essa e a sua comunidade. Cada pessoa aqui confia no que voce esta construindo.',
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


def _build_dashboard_payment_alert_snapshot(*, overdue_payments_queryset):
    qs = overdue_payments_queryset.order_by('due_date')
    payment_alerts = []
    actionable_count = 0
    next_actionable_instance = None

    for p in qs[:10]:
        student = getattr(p, 'student', None)
        # determine if this payment still requires an actionable touch
        contact = None
        try:
            contact = WhatsAppContact.objects.filter(linked_student=student).order_by('-last_outbound_at').first()
        except Exception:
            contact = None

        # If we've recently had an outbound attempt (last_outbound_at exists), consider it non-actionable
        is_actionable = not (contact and getattr(contact, 'last_outbound_at', None))
        if is_actionable:
            actionable_count += 1
            if next_actionable_instance is None:
                next_actionable_instance = p

        payment_alerts.append({
            'id': getattr(p, 'id', None),
            'student': student,
            'student_full_name': getattr(student, 'full_name', None),
            'due_date': getattr(p, 'due_date', None),
            'amount': getattr(p, 'amount', None),
            'href': '/financeiro/',
            'is_actionable': is_actionable,
            'dashboard_requires_whatsapp_followup': bool(contact and getattr(contact, 'last_outbound_at', None)),
        })

    total_count = qs.count()
    total_label = f"{total_count} cobranca(s)" if total_count else 'Nenhuma cobranca'

    return {
        'payment_alerts': payment_alerts,
        'payment_alerts_total_count': total_count,
        'payment_alerts_total_label': total_label,
        'actionable_payment_alerts_count': actionable_count,
        'next_actionable_payment_alert': next_actionable_instance,
    }


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
                f'{count} cobranca(s) prontas pra contato. Eu separei pra voce. Comece por aqui e o dia flui melhor.'
                if role_slug != ROLE_RECEPTION else
                f'{count} cobranca(s) cabem agora no seu turno. Uma por uma, voce resolve. Estou aqui contigo.'
            ),
        }

    if upcoming_sessions:
        primary_session = upcoming_sessions[0]
        starts_at_label = timezone.localtime(primary_session['starts_at']).strftime('%H:%M')
        indicator = primary_session['status_label'] if primary_session['status_label'] == 'Em andamento' else primary_session['occupancy_label']
        copy = (
            f"{primary_session['object'].title} esta rodando agora. Eu cuido do painel, voce cuida do salao."
            if primary_session['status_label'] == 'Em andamento' else
            f"{primary_session['object'].title} comeca as {starts_at_label}. Preparei tudo pra voce so conferir."
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
        'copy': 'Sem urgencias agora. O melhor presente que voce pode dar pro box e cuidar de quem ja esta aqui.',
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

    # --- Weekly revenue computation ---
    def _last_day_of_month(year, month):
        return calendar.monthrange(year, month)[1]

    def _revenue_for_month_week(year, month, week_index):
        # week_index: 1 => days 1-7, 2 => 8-14, etc.
        start_day = 1 + (week_index - 1) * 7
        last_day = _last_day_of_month(year, month)
        end_day = min(start_day + 6, last_day)
        start_date = date(year, month, start_day)
        end_date = date(year, month, end_day)
        total = Payment.objects.filter(
            status=PaymentStatus.PAID,
            due_date__date__gte=start_date,
            due_date__date__lte=end_date,
        ).aggregate(total=Sum('amount'))['total'] or 0
        return total

    # determine current week index in the current month
    week_index = (today.day - 1) // 7 + 1
    this_year = today.year
    this_month = today.month
    # previous month/year
    prev_month_date = (month_start - timedelta(days=1))
    prev_year = prev_month_date.year
    prev_month = prev_month_date.month

    try:
        weekly_total = _revenue_for_month_week(this_year, this_month, week_index)
    except Exception:
        weekly_total = 0

    # Primary previous candidate: previous week in same month (if exists)
    if week_index > 1:
        try:
            previous_week_total = _revenue_for_month_week(this_year, this_month, week_index - 1)
        except Exception:
            previous_week_total = 0
    else:
        # week_index == 1 -> compare with same week index in previous month
        try:
            previous_week_total = _revenue_for_month_week(prev_year, prev_month, 1)
        except Exception:
            previous_week_total = 0

    # Fallback: if previous is zero, try same week index in previous month
    if previous_week_total == 0:
        try:
            fallback = _revenue_for_month_week(prev_year, prev_month, week_index)
            # only use fallback if it's different from current previous
            if fallback:
                previous_week_total = fallback
        except Exception:
            pass

    metrics['weekly_revenue_paid'] = weekly_total
    metrics['weekly_revenue_paid_previous'] = previous_week_total

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

    try:
        payment_alert_snapshot = _build_dashboard_payment_alert_snapshot(overdue_payments_queryset=overdue_payments)
    except NameError:
        total_count = overdue_payments.count()
        payment_alert_snapshot = {
            'payment_alerts': [],
            'payment_alerts_total_count': total_count,
            'payment_alerts_total_label': f"{total_count} cobranca(s)" if total_count else 'Nenhuma cobranca',
            'actionable_payment_alerts_count': total_count,
            'next_actionable_payment_alert': None,
        }
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









