"""
ARQUIVO: builders de cards, alertas e foco visual do snapshot do dashboard.

POR QUE ELE EXISTE:
- tira de `dashboard_snapshot_queries.py` a camada de apresentacao operacional do painel.
"""

from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_RECEPTION
from communications.models import WhatsAppContact


def build_delta_badge(current, previous, *, label, formatter=str, semantic='neutral'):
    try:
        diff = (current or 0) - (previous or 0)
    except Exception:
        diff = 0

    if diff == 0:
        return {
            'tone': 'neutral',
            'value': 'Mesmo ritmo',
            'value_raw': 0,
            'value_percent': 0,
            'is_small': False,
            'label': label,
        }

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


def format_percent(value):
    return f"{int(round(value))}%"


def format_currency(value):
    try:
        normalized_value = float(value or 0)
        rendered = f"{normalized_value:,.2f}"
        rendered = rendered.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {rendered}"
    except Exception:
        return f"R$ {value}"


def build_dashboard_finance_href(role_slug):
    if role_slug == ROLE_RECEPTION:
        return f"{reverse('reception-workspace')}#reception-payment-board"
    return reverse('finance-center')


def build_dashboard_priority_context(*, metrics, pending_intakes_count, today_schedule_occupancy_percent, actionable_payment_alerts_count):
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
    if metrics['sessions_today'] > 0 and today_schedule_occupancy_percent >= 85:
        return {
            'dominant_key': 'occupancy',
            'label': 'session-pressure',
            'reason': 'A agenda do dia virou o primeiro ponto de coordenacao operacional.',
            'lead_order': ['occupancy', 'revenue', 'overdue', 'intakes', 'attendance', 'active'],
        }
    return {
        'dominant_key': 'revenue',
        'label': 'base-health',
        'reason': 'Sem pressao dominante, a receita realizada volta a ser a melhor abertura gerencial.',
        'lead_order': ['revenue', 'overdue', 'intakes', 'occupancy', 'attendance', 'active'],
    }


def build_dashboard_metric_cards_enriched(metrics, *, pending_intakes_count, today_schedule_occupancy_percent, actionable_payment_alerts_count, role_slug=''):
    finance_href = build_dashboard_finance_href(role_slug)
    occupancy_signal_tone = 'good' if today_schedule_occupancy_percent >= 65 else 'neutral'
    occupancy_signal_value = 'Agenda viva' if today_schedule_occupancy_percent >= 65 else 'Dia leve'
    if today_schedule_occupancy_percent >= 95:
        occupancy_signal_tone = 'bad'
        occupancy_signal_value = 'Quase lotado'

    weekly_value = metrics.get('weekly_revenue_paid')
    weekly_previous_value = metrics.get('weekly_revenue_paid_previous')
    current_revenue = weekly_value if weekly_value else metrics['monthly_revenue_paid']
    previous_revenue = weekly_previous_value if weekly_previous_value else metrics['monthly_revenue_paid_previous']
    priority_context = build_dashboard_priority_context(
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
            'display_value': format_currency(current_revenue),
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
            'change': build_delta_badge(
                current_revenue,
                previous_revenue,
                label='vs semana anterior',
                formatter=format_currency,
                semantic='positive',
            ),
            'note': (
                'Sem pressão maior no momento, a receita realizada vira a melhor abertura para ler o pulso do box.'
                if priority_context['dominant_key'] == 'revenue' else
                'Esse é o dinheiro real que entrou. Ele ancora a leitura, mas hoje não abre sozinho a prioridade do dia.'
            ),
            'hide_footer': True,
            'status_hint': 'attention' if priority_context['dominant_key'] == 'revenue' else 'neutral',
        },
        'overdue': {
            'card_class': 'dashboard-kpi-card kpi-red is-panel',
            'eyebrow': 'Cobranças em atraso',
            'kicker': 'Seu primeiro movimento' if priority_context['dominant_key'] == 'overdue' and metrics['overdue_payments'] > 0 else 'Tudo Certo' if metrics['overdue_payments'] == 0 else 'Precisa do seu olhar',
            'display_value': metrics['overdue_payments'],
            'change': build_delta_badge(metrics['overdue_payments'], metrics['overdue_payments_previous_day'], label='desde ontem', semantic='negative'),
            'data_action': 'blink-topbar-finance',
            'note': (
                'Essa é a pressão dominante agora. Cada cobrança aqui ainda tem chance, mas o relógio já está correndo.'
                if priority_context['dominant_key'] == 'overdue' and metrics['overdue_payments'] > 0 else
                'Cada cobrança aqui ainda tem chance. Vou te ajudar a priorizar quem abordar primeiro.'
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
                'Essa é a pressão dominante agora. Cada entrada aqui pode esfriar se ficar para depois.'
                if priority_context['dominant_key'] == 'intakes' and pending_intakes_count > 0 else
                'Cada entrada aqui pode ser alguém que está esperando por você mudar a vida dela.\nVamos cuidar antes que esfrie.'
            ),
            'hide_footer': True,
            'status_hint': 'attention' if pending_intakes_count > 0 else 'clean',
        },
        'occupancy': {
            'card_class': 'dashboard-kpi-card kpi-blue is-ledger',
            'eyebrow': 'Aproveitamento da agenda hoje',
            'kicker': 'Primeira coordenacao do turno' if priority_context['dominant_key'] == 'occupancy' and metrics['sessions_today'] > 0 else 'Pulso do dia',
            'display_value': format_percent(today_schedule_occupancy_percent),
            'signal': {
                'tone': occupancy_signal_tone,
                'value': occupancy_signal_value,
                'label': 'ocupacao media',
            },
            'data_action': 'blink-board-sessions',
            'note': (
                'A agenda virou a primeira coordenação do dia. Vale abrir aqui antes de aprofundar o restante.'
                if priority_context['dominant_key'] == 'occupancy' and metrics['sessions_today'] > 0 else
                'Cuide da lotação para que seu Coach possa entregar uma aula melhor para os alunos.'
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
            'change': build_delta_badge(metrics['attendance_this_month'], metrics['attendance_previous_month'], label='vs mês anterior', semantic='positive'),
            'note': 'Cada presença é uma pessoa que escolheu voltar. Você está construindo algo que importa.',
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
            'note': 'Essa é a sua comunidade. Cada pessoa aqui confia no que você está construindo.',
            'hide_footer': True,
            'status_hint': 'clean',
        },
    }

    if metrics['overdue_payments'] > 0:
        cards['overdue']['href'] = finance_href

    return [cards[key] for key in priority_context['lead_order']], priority_context


def build_dashboard_payment_alert_snapshot(*, overdue_payments_queryset):
    queryset = overdue_payments_queryset.select_related('student').order_by('due_date')
    top_payments = list(queryset[:10])
    student_ids = [payment.student.id for payment in top_payments if payment.student]

    contacts_map = {}
    if student_ids:
        latest_contacts_queryset = WhatsAppContact.objects.filter(
            linked_student_id__in=student_ids
        ).order_by('linked_student_id', '-last_outbound_at', '-id')
        for contact in latest_contacts_queryset:
            if contact.linked_student_id not in contacts_map:
                contacts_map[contact.linked_student_id] = contact

    payment_alerts = []
    actionable_count = 0
    next_actionable_instance = None

    for payment in top_payments:
        student = payment.student
        contact = contacts_map.get(student.id) if student else None
        is_actionable = not (contact and contact.last_outbound_at)
        if is_actionable:
            actionable_count += 1
            if next_actionable_instance is None:
                next_actionable_instance = payment

        payment_alerts.append(
            {
                'id': payment.id,
                'student': student,
                'student_full_name': student.full_name if student else 'Estagiário/Anônimo',
                'due_date': payment.due_date,
                'amount': payment.amount,
                'href': reverse('finance-center'),
                'is_actionable': is_actionable,
                'dashboard_requires_whatsapp_followup': not is_actionable,
            }
        )

    total_count = queryset.count()
    total_label = f"{total_count} cobrança(s)" if total_count else 'Nenhuma cobrança'
    return {
        'payment_alerts': payment_alerts,
        'payment_alerts_total_count': total_count,
        'payment_alerts_total_label': total_label,
        'actionable_payment_alerts_count': actionable_count,
        'next_actionable_payment_alert': next_actionable_instance,
    }


def build_dashboard_glance_summary(*, metrics, role_slug, upcoming_sessions, payment_alert_snapshot):
    finance_href = build_dashboard_finance_href(role_slug)
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
                f'{count} cobrança(s) prontas para contato. Eu separei para você. Comece por aqui e o dia flui melhor.'
                if role_slug != ROLE_RECEPTION else
                f'{count} cobrança(s) cabem agora no seu turno. Uma por uma, você resolve. Estou aqui contigo.'
            ),
        }

    if upcoming_sessions:
        primary_session = upcoming_sessions[0]
        starts_at_label = timezone.localtime(primary_session['starts_at']).strftime('%H:%M')
        indicator = primary_session['status_label'] if primary_session['status_label'] == 'Em andamento' else primary_session['occupancy_label']
        copy = (
            f"{primary_session['object'].title} está rodando agora. Eu cuido do painel, você cuida do salão."
            if primary_session['status_label'] == 'Em andamento' else
            f"{primary_session['object'].title} começa às {starts_at_label}. Preparei tudo para você só conferir."
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
        'copy': 'Sem urgências agora. O melhor presente que você pode dar para o box é cuidar de quem já está aqui.',
    }


__all__ = [
    'build_dashboard_glance_summary',
    'build_dashboard_metric_cards_enriched',
    'build_dashboard_payment_alert_snapshot',
    'format_currency',
]
