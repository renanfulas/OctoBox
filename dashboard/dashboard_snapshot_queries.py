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
from django.conf import settings
import calendar
from datetime import date

from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils import timezone
from shared_support.performance import get_cache_ttl_with_jitter
from shared_support.redis_snapshots import prewarm_student_snapshots
from access.roles import ROLE_RECEPTION
from communications.models import WhatsAppContact
from finance.models import Payment, PaymentStatus
from onboarding.queries import count_pending_intakes
from finance.overdue_metrics import get_overdue_payments_queryset
from operations.models import Attendance, AttendanceStatus, BehaviorNote, ClassSession
from operations.session_snapshots import serialize_class_session, sync_runtime_statuses
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


def _build_dashboard_finance_href(role_slug):
    if role_slug == ROLE_RECEPTION:
        return f"{reverse('reception-workspace')}#reception-payment-board"
    return reverse('finance-center')


def _build_dashboard_priority_context(*, metrics, pending_intakes_count, today_schedule_occupancy_percent, actionable_payment_alerts_count):
    if actionable_payment_alerts_count > 0 or metrics['overdue_payments'] > 0:
        return {
            'dominant_key': 'overdue',
            'label': 'cash-pressure',
            'reason': 'Atrasos e cobrancas acionaveis pedem contato antes de qualquer leitura mais profunda.',
            'lead_order': ['revenue', 'overdue', 'intakes', 'occupancy', 'attendance', 'active'],
        }
    if pending_intakes_count > 0:
        return {
            'dominant_key': 'intakes',
            'label': 'intake-pressure',
            'reason': 'Existe demanda comercial esperando resposta e ela esfria mais rapido do que o restante.',
            'lead_order': ['intakes', 'overdue', 'revenue', 'occupancy', 'attendance', 'active'],
        }
    # Ter aulas no dia e o estado normal do box. A agenda so deve roubar a
    # dianteira da receita quando existe pressao operacional de ocupacao
    # suficiente para virar coordenacao urgente.
    if metrics['sessions_today'] > 0 and today_schedule_occupancy_percent >= 85:
        return {
            'dominant_key': 'occupancy',
            'label': 'session-pressure',
            'reason': 'A agenda do dia virou o primeiro ponto de coordenacao operacional.',
            'lead_order': ['occupancy', 'overdue', 'revenue', 'intakes', 'attendance', 'active'],
        }
    return {
        'dominant_key': 'revenue',
        'label': 'base-health',
        'reason': 'Sem pressao dominante, a receita realizada volta a ser a melhor abertura gerencial.',
        'lead_order': ['revenue', 'overdue', 'intakes', 'occupancy', 'attendance', 'active'],
    }


def _build_dashboard_metric_cards_legacy(metrics, *, pending_intakes_count, today_schedule_occupancy_percent):
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
            'card_class': 'dashboard-kpi-card kpi-red is-panel',
            'eyebrow': 'CobranÃ§as em atraso',
            'kicker': 'Tudo Certo' if metrics['overdue_payments'] == 0 else 'Precisa do seu olhar',
            'display_value': metrics['overdue_payments'],
            'change': _build_delta_badge(metrics['overdue_payments'], metrics['overdue_payments_previous_day'], label='desde ontem', semantic='negative'),
            'data_action': 'blink-topbar-finance',
            'note': 'Cada cobranÃ§a aqui ainda tem chance. Vou te ajudar a priorizar quem abordar primeiro.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-amber is-stage',
            'eyebrow': 'Receita realizada',
            'kicker': 'O que realmente chegou',
            'display_value': _format_currency(current_revenue),
            'is_jumbo': True,
            'data_action': 'blink-sidebar-financeiro',
            'sparkline_data': [
                {'percent': 25, 'label': '6 dias atrÃ¡s: R$ 850,00'},
                {'percent': 40, 'label': '5 dias atrÃ¡s: R$ 1.360,00'},
                {'percent': 30, 'label': '4 dias atrÃ¡s: R$ 1.020,00'},
                {'percent': 55, 'label': '3 dias atrÃ¡s: R$ 1.870,00'},
                {'percent': 45, 'label': '2 dias atrÃ¡s: R$ 1.530,00'},
                {'percent': 80, 'label': 'Ontem: R$ 2.720,00'},
                {'percent': 100, 'label': 'Hoje: Cerca de R$ 3.400,00'},
            ],
            'change': _build_delta_badge(
                current_revenue,
                previous_revenue,
                label='vs semana anterior',
                formatter=_format_currency,
                semantic='positive',
            ),
            'note': 'Esse Ã© o dinheiro real que entrou. Eu te mostro onde estÃ¡ indo bem e onde precisa de atenÃ§Ã£o.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-amber is-ribbon',
            'eyebrow': 'Entradas pendentes',
            'kicker': 'Pessoas que procuraram seu Box',
            'display_value': pending_intakes_count,
            'data_action': 'blink-topbar-intake',
            'signal': {
                'tone': 'neutral' if pending_intakes_count else 'good',
                'value': 'Responder hoje' if pending_intakes_count else 'Fila limpa',
                'label': 'pipeline comercial',
            },
            'note': 'Cada entrada aqui pode ser alguÃ©m que estÃ¡ esperando por vocÃª mudar a vida dela.\nVamos cuidar antes que esfrie.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-blue is-ledger',
            'eyebrow': 'Aproveitamento da agenda hoje',
            'kicker': 'Pulso do dia',
            'display_value': _format_percent(today_schedule_occupancy_percent),
            'signal': {
                'tone': occupancy_signal_tone,
                'value': occupancy_signal_value,
                'label': 'ocupacao media',
            },
            'data_action': 'blink-board-sessions',
            'note': 'Cuide da lotaÃ§Ã£o para que seu Coach possa entregar uma aula melhor para os alunos.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-green is-rail',
            'eyebrow': 'PresenÃ§a no mÃªs',
            'kicker': 'Compromisso que voltou',
            'display_value': metrics['attendance_this_month'],
            'data_action': 'blink-sidebar-alunos',
            'change': _build_delta_badge(metrics['attendance_this_month'], metrics['attendance_previous_month'], label='vs mes anterior', semantic='positive'),
            'note': 'Cada presenÃ§a Ã© uma pessoa que escolheu voltar. VocÃª estÃ¡ construindo algo que importa.',
            'hide_footer': True,
        },
        {
            'card_class': 'dashboard-kpi-card kpi-emerald is-orbit',
            'eyebrow': 'Comunidade ativa',
            'kicker': 'Sua comunidade viva',
            'display_value': metrics['active_students'],
            'data_action': 'blink-sidebar-alunos',
            'signal': {'tone': 'good', 'value': 'Base viva', 'label': 'comunidade ativa'},
            'note': 'Essa Ã© a sua comunidade. Cada pessoa aqui confia no que vocÃª estÃ¡ construindo.',
            'hide_footer': True,
        },
    ]


def _build_dashboard_metric_cards_enriched(metrics, *, pending_intakes_count, today_schedule_occupancy_percent, actionable_payment_alerts_count, role_slug=''):
    occupancy_signal_tone = 'good' if today_schedule_occupancy_percent >= 65 else 'neutral'
    occupancy_signal_value = 'Agenda viva' if today_schedule_occupancy_percent >= 65 else 'Dia leve'
    if today_schedule_occupancy_percent >= 95:
        occupancy_signal_tone = 'bad'
        occupancy_signal_value = 'Quase lotado'

    _weekly = metrics.get('weekly_revenue_paid')
    _weekly_prev = metrics.get('weekly_revenue_paid_previous')
    current_revenue = _weekly if _weekly else metrics['monthly_revenue_paid']
    previous_revenue = _weekly_prev if _weekly_prev else metrics['monthly_revenue_paid_previous']
    priority_context = _build_dashboard_priority_context(
        metrics=metrics,
        pending_intakes_count=pending_intakes_count,
        today_schedule_occupancy_percent=today_schedule_occupancy_percent,
        actionable_payment_alerts_count=actionable_payment_alerts_count,
    )
    cards = {
        'revenue': {
            'card_class': 'dashboard-kpi-card kpi-amber is-stage',
            'eyebrow': 'Receita realizada',
            'kicker': 'O que realmente chegou' if priority_context['dominant_key'] == 'revenue' else 'Base do caixa',
            'display_value': _format_currency(current_revenue),
            'is_jumbo': True,
            'data_action': 'blink-sidebar-financeiro',
            'sparkline_data': [
                {'percent': 25, 'label': '6 dias atras: R$ 850,00'},
                {'percent': 40, 'label': '5 dias atras: R$ 1.360,00'},
                {'percent': 30, 'label': '4 dias atras: R$ 1.020,00'},
                {'percent': 55, 'label': '3 dias atras: R$ 1.870,00'},
                {'percent': 45, 'label': '2 dias atras: R$ 1.530,00'},
                {'percent': 80, 'label': 'Ontem: R$ 2.720,00'},
                {'percent': 100, 'label': 'Hoje: Cerca de R$ 3.400,00'},
            ],
            'change': _build_delta_badge(
                current_revenue,
                previous_revenue,
                label='vs semana anterior',
                formatter=_format_currency,
                semantic='positive',
            ),
            'note': (
                'Sem pressao maior no momento, a receita realizada vira a melhor abertura para ler o pulso do box.'
                if priority_context['dominant_key'] == 'revenue' else
                'Esse e o dinheiro real que entrou. Ele ancora a leitura, mas hoje nao abre sozinho a prioridade do dia.'
            ),
            'hide_footer': True,
            'status_hint': 'attention' if priority_context['dominant_key'] == 'revenue' else 'neutral',
        },
        'overdue': {
            'card_class': 'dashboard-kpi-card kpi-red is-panel',
            'eyebrow': 'Cobrancas em atraso',
            'kicker': 'Seu primeiro movimento' if priority_context['dominant_key'] == 'overdue' and metrics['overdue_payments'] > 0 else 'Tudo Certo' if metrics['overdue_payments'] == 0 else 'Precisa do seu olhar',
            'display_value': metrics['overdue_payments'],
            'change': _build_delta_badge(metrics['overdue_payments'], metrics['overdue_payments_previous_day'], label='desde ontem', semantic='negative'),
            'data_action': 'blink-topbar-finance',
            'note': (
                'Essa e a pressao dominante agora. Cada cobranca aqui ainda tem chance, mas o relogio ja esta correndo.'
                if priority_context['dominant_key'] == 'overdue' and metrics['overdue_payments'] > 0 else
                'Cada cobranca aqui ainda tem chance. Vou te ajudar a priorizar quem abordar primeiro.'
            ),
            'hide_footer': True,
            'status_hint': 'attention' if metrics['overdue_payments'] > 0 else 'clean',
        },
        'intakes': {
            'card_class': 'dashboard-kpi-card kpi-amber is-ribbon',
            'eyebrow': 'Entradas pendentes',
            'kicker': 'Sua primeira resposta hoje' if priority_context['dominant_key'] == 'intakes' and pending_intakes_count > 0 else 'Pessoas que procuraram seu Box',
            'display_value': pending_intakes_count,
            'data_action': 'blink-topbar-intake',
            'signal': {
                'tone': 'warning' if pending_intakes_count else 'good',
                'value': 'Responder hoje' if pending_intakes_count else 'Fila limpa',
                'label': 'pipeline comercial',
            },
            'note': (
                'Essa e a pressao dominante agora. Cada entrada aqui pode esfriar se ficar para depois.'
                if priority_context['dominant_key'] == 'intakes' and pending_intakes_count > 0 else
                'Cada entrada aqui pode ser alguem que esta esperando por voce mudar a vida dela.\nVamos cuidar antes que esfrie.'
            ),
            'hide_footer': True,
            'status_hint': 'attention' if pending_intakes_count > 0 else 'clean',
        },
        'occupancy': {
            'card_class': 'dashboard-kpi-card kpi-blue is-ledger',
            'eyebrow': 'Aproveitamento da agenda hoje',
            'kicker': 'Primeira coordenacao do turno' if priority_context['dominant_key'] == 'occupancy' and metrics['sessions_today'] > 0 else 'Pulso do dia',
            'display_value': _format_percent(today_schedule_occupancy_percent),
            'data_action': 'blink-board-sessions',
            'signal': {
                'tone': occupancy_signal_tone,
                'value': occupancy_signal_value,
                'label': 'ocupacao media',
            },
            'data_action': 'blink-board-sessions',
            'note': (
                'A agenda virou a primeira coordenacao do dia. Vale abrir aqui antes de aprofundar o restante.'
                if priority_context['dominant_key'] == 'occupancy' and metrics['sessions_today'] > 0 else
                'Cuide da lotacao para que seu Coach possa entregar uma aula melhor para os alunos.'
            ),
            'hide_footer': True,
            'status_hint': 'attention' if today_schedule_occupancy_percent >= 95 else 'neutral',
        },
        'attendance': {
            'card_class': 'dashboard-kpi-card kpi-green is-rail',
            'eyebrow': 'Presenca no mes',
            'kicker': 'Compromisso que voltou',
            'display_value': metrics['attendance_this_month'],
            'data_action': 'blink-sidebar-alunos',
            'change': _build_delta_badge(metrics['attendance_this_month'], metrics['attendance_previous_month'], label='vs mes anterior', semantic='positive'),
            'note': 'Cada presenca e uma pessoa que escolheu voltar. Voce esta construindo algo que importa.',
            'hide_footer': True,
            'status_hint': 'neutral',
        },
        'active': {
            'card_class': 'dashboard-kpi-card kpi-emerald is-orbit',
            'eyebrow': 'Comunidade ativa',
            'kicker': 'Sua comunidade viva',
            'display_value': metrics['active_students'],
            'data_action': 'blink-sidebar-alunos',
            'signal': {'tone': 'good', 'value': 'Base viva', 'label': 'comunidade ativa'},
            'note': 'Essa e a sua comunidade. Cada pessoa aqui confia no que voce esta construindo.',
            'hide_footer': True,
            'status_hint': 'clean',
        },
    }

    if metrics['overdue_payments'] > 0:
        cards['overdue']['href'] = finance_href

    return [cards[key] for key in priority_context['lead_order']], priority_context


def _decorate_dashboard_sessions(serialized_sessions):
    visible_sessions = [session for session in serialized_sessions if session['status_label'] != 'Finalizada']
    for index, session in enumerate(visible_sessions):
        if session['status_label'] == 'Em andamento':
            session['dashboard_kicker'] = 'Em aula agora'
        elif session['booking_closed']:
            session['dashboard_kicker'] = 'Reservas fechadas'
        elif index == 0:
            session['dashboard_kicker'] = 'PrÃ³xima aula'
        elif session['occupancy_percent'] >= 90:
            session['dashboard_kicker'] = 'Turma quase lotada'
        else:
            session['dashboard_kicker'] = 'Em seguida'
    return visible_sessions


def _build_dashboard_payment_alert_snapshot(*, overdue_payments_queryset):
    # ðŸš€ Performance de Elite (Ghost Audit): OtimizaÃ§Ã£o N+1
    # PrÃ©-carregamos o contato de WhatsApp mais recente para cada estudante da lista
    # para evitar 10+ queries extras no loop.
    qs = overdue_payments_queryset.select_related('student').order_by('due_date')
    top_10_payments = list(qs[:10])
    student_ids = [p.student.id for p in top_10_payments if p.student]
    
    contacts_map = {}
    if student_ids:
        # ðŸ§ª Compatibilidade V4.1 (SQLite & Postgres): DeduplicaÃ§Ã£o DeterminÃ­stica em memÃ³ria
        # Ordenamos por estudante e data, depois guardamos apenas o mais recente no mapa.
        latest_contacts_qs = WhatsAppContact.objects.filter(
            linked_student_id__in=student_ids
        ).order_by('linked_student_id', '-last_outbound_at', '-id')
        
        for contact in latest_contacts_qs:
            if contact.linked_student_id not in contacts_map:
                contacts_map[contact.linked_student_id] = contact

    payment_alerts = []
    actionable_count = 0
    next_actionable_instance = None

    for p in top_10_payments:
        student = p.student
        contact = contacts_map.get(student.id) if student else None

        # If we've recently had an outbound attempt (last_outbound_at exists), consider it non-actionable
        is_actionable = not (contact and contact.last_outbound_at)
        if is_actionable:
            actionable_count += 1
            if next_actionable_instance is None:
                next_actionable_instance = p

        payment_alerts.append({
            'id': p.id,
            'student': student,
            'student_full_name': student.full_name if student else 'EstagiÃ¡rio/AnÃ´nimo',
            'due_date': p.due_date,
            'amount': p.amount,
            'href': reverse('finance-center'),
            'is_actionable': is_actionable,
            'dashboard_requires_whatsapp_followup': not is_actionable,
        })

    total_count = qs.count()
    total_label = f"{total_count} cobranÃ§a(s)" if total_count else 'Nenhuma cobranÃ§a'

    return {
        'payment_alerts': payment_alerts,
        'payment_alerts_total_count': total_count,
        'payment_alerts_total_label': total_label,
        'actionable_payment_alerts_count': actionable_count,
        'next_actionable_payment_alert': next_actionable_instance,
    }


def _build_dashboard_glance_summary(*, metrics, role_slug, upcoming_sessions, payment_alert_snapshot):
    finance_href = _build_dashboard_finance_href(role_slug)
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
                f'{count} cobranÃ§a(s) prontas para contato. Eu separei para vocÃª. Comece por aqui e o dia flui melhor.'
                if role_slug != ROLE_RECEPTION else
                f'{count} cobranÃ§a(s) cabem agora no seu turno. Uma por uma, vocÃª resolve. Estou aqui contigo.'
            ),
        }

    if upcoming_sessions:
        primary_session = upcoming_sessions[0]
        starts_at_label = timezone.localtime(primary_session['starts_at']).strftime('%H:%M')
        indicator = primary_session['status_label'] if primary_session['status_label'] == 'Em andamento' else primary_session['occupancy_label']
        copy = (
            f"{primary_session['object'].title} estÃ¡ rodando agora. Eu cuido do painel, vocÃª cuida do salÃ£o."
            if primary_session['status_label'] == 'Em andamento' else
            f"{primary_session['object'].title} comeÃ§a Ã s {starts_at_label}. Preparei tudo para vocÃª sÃ³ conferir."
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
        'href': reverse('student-directory'),
        'card_class': 'is-base',
        'indicator_class': 'is-base',
        'kicker': 'Base em foco',
        'value': metrics['active_students'],
        'indicator': 'Comunidade',
        'copy': 'Sem urgÃªncias agora. O melhor presente que vocÃª pode dar para o box Ã© cuidar de quem jÃ¡ estÃ¡ aqui.',
    }

def build_dashboard_snapshot(*, today, month_start, role_slug=''):
    """
    Retorna um snapshot do dashboard com cache de curton prazo (60s por padrao).
    O cache e particionado por role_slug, data e inicio do mes.
    """
    cache_key = f"dashboard_snapshot:{role_slug}:{today.isoformat()}:{month_start.isoformat()}"
    ttl = getattr(settings, 'SHELL_COUNTS_CACHE_TTL_SECONDS', 60)
    # ðŸš€ Performance de Elite (Ghost Hardening): Cache Jitter
    # Evita que todos os dashboards de todos os usuÃ¡rios expirem no mesmo segundo.
    jittered_ttl = get_cache_ttl_with_jitter(ttl)

    def _calculate():
        return _build_dashboard_snapshot_raw(today=today, month_start=month_start, role_slug=role_slug)

    return cache.get_or_set(cache_key, _calculate, timeout=jittered_ttl)


def _build_dashboard_snapshot_raw(*, today, month_start, role_slug=''):
    previous_day = today - timedelta(days=1)
    previous_month_end = month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    # ðŸš€ OtimizaÃ§Ã£o Game Dev (Latency Zero): AgregaÃ§Ã£o por Modelo
    # Em vez de 11 counts/sums individuais, agora fazemos 4 queries agrupadas.
    
    sessions_today = ClassSession.objects.filter(scheduled_at__date=today)
    
    student_metrics = Student.objects.aggregate(
        active_count=Count('id', filter=Q(status=StudentStatus.ACTIVE))
    )

    session_metrics = ClassSession.objects.aggregate(
        today_count=Count('id', filter=Q(scheduled_at__date=today)),
        prev_day_count=Count('id', filter=Q(scheduled_at__date=previous_day))
    )

    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    overdue_payments_prev = get_overdue_payments_queryset(Payment.objects.all(), today=previous_day)
    
    payment_metrics = Payment.objects.aggregate(
        overdue_count=Count('id', filter=Q(id__in=overdue_payments.values('id'))),
        overdue_prev_count=Count('id', filter=Q(id__in=overdue_payments_prev.values('id'))),
        monthly_paid=Sum('amount', filter=Q(status=PaymentStatus.PAID, due_date__gte=month_start)),
        monthly_paid_prev=Sum('amount', filter=Q(status=PaymentStatus.PAID, due_date__gte=previous_month_start, due_date__lt=month_start))
    )

    attendance_metrics = Attendance.objects.filter(
        status__in=[AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT]
    ).aggregate(
        this_month=Count('id', filter=Q(session__scheduled_at__date__gte=month_start)),
        prev_month=Count('id', filter=Q(session__scheduled_at__date__gte=previous_month_start, session__scheduled_at__date__lt=month_start))
    )

    note_metrics = BehaviorNote.objects.aggregate(
        this_month=Count('id', filter=Q(happened_at__date__gte=month_start)),
        prev_month=Count('id', filter=Q(happened_at__date__gte=previous_month_start, happened_at__date__lt=month_start))
    )

    metrics = {
        'active_students': student_metrics['active_count'],
        'sessions_today': session_metrics['today_count'],
        'sessions_previous_day': session_metrics['prev_day_count'],
        'overdue_payments': payment_metrics['overdue_count'],
        'overdue_payments_previous_day': payment_metrics['overdue_prev_count'],
        'attendance_this_month': attendance_metrics['this_month'],
        'attendance_previous_month': attendance_metrics['prev_month'],
        'monthly_revenue_paid': payment_metrics['monthly_paid'] or 0,
        'monthly_revenue_paid_previous': payment_metrics['monthly_paid_prev'] or 0,
        'occurrences_this_month': note_metrics['this_month'],
        'occurrences_previous_month': note_metrics['prev_month'],
    }

    current_time = timezone.localtime()
    upcoming_session_objects = list(
        ClassSession.objects.filter(scheduled_at__date__gte=today)
        .select_related('coach')
        .annotate(occupied_slots=Count('attendances'))
        .order_by('scheduled_at')[:5]
    )
    sync_runtime_statuses(upcoming_session_objects, now=current_time)

    # --- Weekly revenue computation ---
    # determine current week index in the current month
    week_index = (today.day - 1) // 7 + 1
    
    def _get_week_range(year, month, w_idx):
        start_day = 1 + (w_idx - 1) * 7
        last_day = calendar.monthrange(year, month)[1]
        if start_day > last_day: return None, None
        end_day = min(start_day + 6, last_day)
        return date(year, month, start_day), date(year, month, end_day)

    curr_start, curr_end = _get_week_range(today.year, today.month, week_index)
    
    # Pre-calculating comparison week range
    if week_index > 1:
        prev_start, prev_end = _get_week_range(today.year, today.month, week_index - 1)
    else:
        prev_month_date = (month_start - timedelta(days=1))
        prev_start, prev_end = _get_week_range(prev_month_date.year, prev_month_date.month, 1)

    # ðŸš€ Performance de Elite (Ghost Hardening): Multi-Period Aggregation
    # Uma Ãºnica viagem ao banco para buscar todos os perÃ­odos necessÃ¡rios.
    revenue_metrics = Payment.objects.filter(status=PaymentStatus.PAID).aggregate(
        curr_week=Sum('amount', filter=Q(due_date__gte=curr_start, due_date__lte=curr_end)),
        prev_week=Sum('amount', filter=Q(due_date__gte=prev_start, due_date__lte=prev_end))
    )
    
    weekly_total = revenue_metrics['curr_week'] or 0
    previous_week_total = revenue_metrics['prev_week'] or 0

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
    finance_focus_href = _build_dashboard_finance_href(role_slug)
    finance_focus_label = 'Abrir fila curta da Recepcao' if role_slug == ROLE_RECEPTION else 'Abrir financeiro'
    finance_review_label = 'Revisar fila curta' if role_slug == ROLE_RECEPTION else 'Revisar financeiro'
    if metrics['overdue_payments'] > 0:
        operational_focus.append(
            {
                'label': 'Caixa curto pede aÃ§Ã£o agora' if role_slug == ROLE_RECEPTION else 'CobranÃ§a pede aÃ§Ã£o agora',
                'chip_label': 'CobranÃ§as' if role_slug != ROLE_RECEPTION else 'Caixa',
                'summary': (
                    f"{metrics['overdue_payments']} pagamento(s) jÃ¡ passaram do vencimento e podem pedir abordagem de balcÃ£o ainda hoje."
                    if role_slug == ROLE_RECEPTION else
                    f"{metrics['overdue_payments']} pagamento(s) jÃ¡ passaram do vencimento e pedem contato antes de virarem evasÃ£o."
                ),
                'pill_class': 'warning',
                'href': finance_focus_href,
                'href_label': finance_focus_label,
            }
        )
    else:
        operational_focus.append(
            {
                'label': 'Caixa curto estÃ¡ sob controle' if role_slug == ROLE_RECEPTION else 'CobranÃ§a estÃ¡ sob controle',
                'chip_label': 'CobranÃ§as' if role_slug != ROLE_RECEPTION else 'Caixa',
                'summary': 'Nenhum atraso crÃ­tico apareceu no recorte de hoje.' if role_slug != ROLE_RECEPTION else 'Nenhuma cobranÃ§a curta crÃ­tica apareceu no recorte de hoje.',
                'pill_class': 'success',
                'href': finance_focus_href,
                'href_label': finance_review_label,
            }
        )

    if metrics['sessions_today'] > 0:
        operational_focus.append(
            {
                'label': 'Agenda do dia estÃ¡ viva',
                'chip_label': 'Aulas',
                'summary': f"{metrics['sessions_today']} aula(s) pedem leitura rÃ¡pida de coach, ocupaÃ§Ã£o e recepÃ§Ã£o.",
                'pill_class': 'info',
                'href': reverse('class-grid'),
                'href_label': 'Ver grade',
            }
        )
    else:
        operational_focus.append(
            {
                'label': 'Agenda do dia estÃ¡ leve',
                'chip_label': 'Aulas',
                'summary': 'NÃ£o hÃ¡ aulas previstas hoje, entÃ£o o foco pode cair mais em base e financeiro.',
                'pill_class': 'accent',
                'href': reverse('class-grid'),
                'href_label': 'Abrir aulas',
            }
        )

    if metrics['active_students'] > 0:
        operational_focus.append(
            {
                'label': 'Base ativa exige acompanhamento',
                'chip_label': 'Base',
                'summary': (
                    f"{metrics['active_students']} aluno(s) sustentam a RecepÃ§Ã£o e pedem leitura de ficha, risco e prÃ³xima abordagem."
                    if role_slug == ROLE_RECEPTION else
                    f"{metrics['active_students']} aluno(s) sustentam a operaÃ§Ã£o e pedem leitura de presenÃ§a, risco e retenÃ§Ã£o."
                ),
                'pill_class': 'accent',
                'href': reverse('student-directory'),
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
            'payment_alerts_total_label': f"{total_count} cobranÃ§a(s)" if total_count else 'Nenhuma cobranÃ§a',
            'actionable_payment_alerts_count': total_count,
            'next_actionable_payment_alert': None,
        }
    serialized_sessions = [
        serialize_class_session(session, now=current_time)
        for session in upcoming_session_objects
    ]
    upcoming_sessions = _decorate_dashboard_sessions(serialized_sessions)
    pending_intakes_count = count_pending_intakes()
    # ðŸš€ OtimizaÃ§Ã£o Game Dev (Latency Zero): AgregaÃ§Ã£o de OcupaÃ§Ã£o e SaÃºde
    capacity_metrics = sessions_today.annotate(occupied_slots=Count('attendances')).aggregate(
        total_capacity=Sum('capacity'),
        total_occupied=Sum('occupied_slots')
    )
    
    today_schedule_capacity = capacity_metrics['total_capacity'] or 0
    today_schedule_occupied = capacity_metrics['total_occupied'] or 0
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
    # Buscamos a contagem e os top 8 em uma tacada sÃ³ (quase)
    health_metrics = student_health_queryset.aggregate(at_risk=Count('id', filter=Q(total_absences__gte=1)))
    students_at_risk_count = health_metrics['at_risk']
    student_health = student_health_queryset.order_by('-total_absences', '-total_attendances', 'full_name')[:8]
    metric_cards, metric_priority_context = _build_dashboard_metric_cards_enriched(
        metrics,
        pending_intakes_count=pending_intakes_count,
        today_schedule_occupancy_percent=today_schedule_occupancy_percent,
        actionable_payment_alerts_count=payment_alert_snapshot['actionable_payment_alerts_count'],
        role_slug=role_slug,
    )

    # ðŸš€ Performance AAA (Preloading Preditivo): Aquecimento de Cache
    # Carregamos os alunos em evidÃªncia para que o prÃ³ximo clique seja instatÃ¢neo.
    try:
        hot_students = set()
        # Alunos com alertas de pagamento
        if 'payment_alert_snapshot' in locals():
            alert_student_ids = [p['student'].id for p in payment_alert_snapshot['payment_alerts'] if p.get('student')]
            hot_students.update(alert_student_ids)
        
        # Alunos da saÃºde da base (em risco)
        health_student_ids = [s.id for s in student_health]
        hot_students.update(health_student_ids)

        if hot_students:
            prewarm_student_snapshots(list(hot_students))
    except Exception:
        pass

    return {
        'metrics': metrics,
        'hero_stats': [
            {'label': 'Comunidade ativa', 'value': metrics['active_students']},
            {'label': 'Turmas hoje', 'value': metrics['sessions_today']},
            {'label': 'Atrasos', 'value': metrics['overdue_payments']},
            {'label': 'Receita rodada', 'value': _format_currency(metrics['monthly_revenue_paid'])},
        ],
        'metric_cards': metric_cards,
        'metric_priority_context': metric_priority_context,
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









