"""
ARQUIVO: corredor de leitura do workspace de owner.

POR QUE ELE EXISTE:
- tira de `operations/queries.py` a leitura executiva do owner sem alterar o contrato atual.

O QUE ESTE ARQUIVO FAZ:
1. monta headline metrics e sessoes do dia para owner.
2. organiza foco operacional e decision entry context.
3. fecha o payload executivo do owner.

PONTOS CRITICOS:
- manter o snapshot estavel enquanto a fronteira ainda convive com `queries.py`.
"""

from datetime import timedelta

from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone

from communications.queries import build_communications_headline_metrics
from finance.models import Enrollment, EnrollmentStatus, Payment
from finance.overdue_metrics import get_overdue_payments_queryset, sum_overdue_amount
from monitoring.beacon_snapshot import build_red_beacon_snapshot
from operations.models import ClassSession
from operations.session_snapshots import serialize_class_session, sync_runtime_statuses
from shared_support.workspace_snapshot_versions import build_workspace_snapshot_version
from students.models import Student


def _build_metric_card(card_class, eyebrow, value, note=None):
    card = {
        'card_class': card_class,
        'eyebrow': eyebrow,
        'display_value': value,
    }
    if note:
        card['note'] = note
    return card


def _build_owner_focus_item(*, key, label, summary, count, pill_class, href, href_label, chip_label=''):
    return {
        'key': key,
        'label': label,
        'chip_label': chip_label,
        'summary': summary,
        'count': count,
        'pill_class': pill_class,
        'href': href,
        'href_label': href_label,
        'is_clickable': (count or 0) > 0,
    }


def _build_decision_entry_context(entry_item=None, secondary_item=None):
    entry_item = entry_item or {}
    secondary_item = secondary_item or {}
    return {
        'entry_key': entry_item.get('key', ''),
        'entry_surface': entry_item.get('key', ''),
        'entry_href': entry_item.get('href', ''),
        'entry_href_label': entry_item.get('href_label', 'Abrir'),
        'entry_label': entry_item.get('label', ''),
        'entry_reason': entry_item.get('summary', ''),
        'entry_count': entry_item.get('count'),
        'entry_pill_class': entry_item.get('pill_class', 'accent'),
        'secondary_key': secondary_item.get('key', ''),
        'secondary_surface': secondary_item.get('key', ''),
        'secondary_href': secondary_item.get('href', ''),
        'secondary_href_label': secondary_item.get('href_label', 'Abrir'),
        'secondary_label': secondary_item.get('label', ''),
        'secondary_reason': secondary_item.get('summary', ''),
    }


def _count_ghost_enrollments(*, today):
    """Matrículas ACTIVE sem nenhuma cobrança com due_date nos últimos 30 dias."""
    cutoff = today - timedelta(days=30)
    return (
        Enrollment.objects
        .filter(status=EnrollmentStatus.ACTIVE)
        .annotate(recent_payments=Count('payments', filter=Q(payments__due_date__gte=cutoff)))
        .filter(recent_payments=0)
        .count()
    )


def _decorate_operational_sessions(serialized_sessions):
    visible_sessions = [session for session in serialized_sessions if session['status_label'] != 'Finalizada']
    for index, session in enumerate(visible_sessions):
        if session['status_label'] == 'Em andamento':
            session['dashboard_kicker'] = 'Em aula agora'
        elif session['booking_closed']:
            session['dashboard_kicker'] = 'Reservas fechadas'
        elif index == 0:
            session['dashboard_kicker'] = 'Próxima aula'
        elif session['occupancy_percent'] >= 90:
            session['dashboard_kicker'] = 'Turma quase lotada'
        else:
            session['dashboard_kicker'] = 'Em seguida'
    return visible_sessions


def build_owner_workspace_snapshot(*, today):
    red_beacon_snapshot = build_red_beacon_snapshot()
    communications_metrics = build_communications_headline_metrics(today=today)
    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    overdue_amount = sum_overdue_amount(Payment.objects.all(), today=today)
    ghost_enrollments_count = _count_ghost_enrollments(today=today)
    classes_today = ClassSession.objects.filter(scheduled_at__date=today).count()
    current_time = timezone.localtime()
    owner_session_objects = list(
        ClassSession.objects.filter(scheduled_at__date=today)
        .select_related('coach')
        .annotate(occupied_slots=Count('attendances'))
        .order_by('scheduled_at')[:5]
    )
    sync_runtime_statuses(owner_session_objects, now=current_time)
    owner_upcoming_sessions = _decorate_operational_sessions(
        [serialize_class_session(session, now=current_time) for session in owner_session_objects]
    )
    headline_metrics = {
        'students': Student.objects.count(),
        'pending_intakes': communications_metrics['pending_intakes'],
        'whatsapp_contacts': communications_metrics['whatsapp_contacts'],
        'messages_logged': communications_metrics['messages_logged'],
        'overdue_payments': overdue_payments.count(),
        'overdue_amount': overdue_amount,
        'ghost_enrollments': ghost_enrollments_count,
    }
    focus_map = {
        'intakes': _build_owner_focus_item(
            key='intakes',
            label='Ver entradas',
            chip_label='Entradas',
            summary=(
                f"{headline_metrics['pending_intakes']} entrada(s) esperam resposta."
                if headline_metrics['pending_intakes']
                else 'Nenhuma entrada espera resposta agora.'
            ),
            count=headline_metrics['pending_intakes'],
            pill_class='danger' if headline_metrics['pending_intakes'] > 0 else 'success',
            href=reverse('intake-center'),
            href_label='Abrir entradas',
        ),
        'payments': _build_owner_focus_item(
            key='payments',
            label='Ver cobranças',
            chip_label='Cobrança',
            summary=(
                f"{headline_metrics['overdue_payments']} cobrança(s) estão atrasadas e pedem contato."
                if headline_metrics['overdue_payments']
                else 'Nenhuma cobrança atrasada pede contato agora.'
            ),
            count=headline_metrics['overdue_payments'],
            pill_class='danger' if headline_metrics['overdue_payments'] > 0 else 'success',
            href=reverse('finance-center'),
            href_label='Abrir cobranças',
        ),
        'structure': _build_owner_focus_item(
            key='structure',
            label='Ver estrutura',
            chip_label='Estrutura',
            summary=(
                f"{headline_metrics['whatsapp_contacts']} contato(s) com WhatsApp e {headline_metrics['messages_logged']} conversa(s) salvas."
            ),
            count=headline_metrics['whatsapp_contacts'],
            pill_class='success',
            href=reverse('student-directory'),
            href_label='Abrir estrutura',
        ),
        'ghost_enrollments': _build_owner_focus_item(
            key='ghost_enrollments',
            label='Matriculas sem cobranca',
            chip_label='Alerta',
            summary=(
                f"{headline_metrics['ghost_enrollments']} matricula(s) ativa(s) sem cobranca nos ultimos 30 dias. Verifique se a recorrencia foi configurada."
                if headline_metrics['ghost_enrollments']
                else 'Todas as matriculas ativas tem cobranca recente vinculada.'
            ),
            count=headline_metrics['ghost_enrollments'],
            pill_class='danger' if headline_metrics['ghost_enrollments'] > 0 else 'success',
            href=reverse('finance-center'),
            href_label='Abrir financeiro',
        ),
    }
    if headline_metrics['ghost_enrollments'] > 0:
        focus_order = ['ghost_enrollments', 'payments', 'intakes']
    elif headline_metrics['pending_intakes'] > 0:
        focus_order = ['intakes', 'payments', 'structure']
    elif headline_metrics['overdue_payments'] > 0:
        focus_order = ['payments', 'intakes', 'structure']
    else:
        focus_order = ['structure', 'intakes', 'payments']
    owner_operational_focus = [focus_map[key] for key in focus_order]
    owner_decision_entry_context = _build_decision_entry_context(
        owner_operational_focus[0] if owner_operational_focus else None,
        owner_operational_focus[1] if len(owner_operational_focus) > 1 else None,
    )
    snapshot_version = build_workspace_snapshot_version(
        {'key': 'students', 'count': headline_metrics['students']},
        {'key': 'intakes', 'count': headline_metrics['pending_intakes']},
        {'key': 'contacts', 'count': headline_metrics['whatsapp_contacts']},
        {'key': 'messages', 'count': headline_metrics['messages_logged']},
        {'key': 'overdue', 'count': headline_metrics['overdue_payments']},
        {'key': 'sessions', 'items': owner_session_objects, 'count': len(owner_upcoming_sessions)},
        {'key': 'ghost_enrollments', 'count': headline_metrics['ghost_enrollments']},
    )
    transport_payload = {
        'owner_upcoming_sessions': owner_upcoming_sessions,
    }
    return {
        'snapshot_version': snapshot_version,
        'headline_metrics': headline_metrics,
        'classes_today': classes_today,
        'owner_priority_surface': (owner_operational_focus[0] if owner_operational_focus else {}).get('key', 'structure'),
        'overdue_amount_label': f"R$ {overdue_amount:.2f}".replace('.', ','),
        'owner_upcoming_sessions': owner_upcoming_sessions,
        'owner_upcoming_sessions_total_label': f"{len(owner_upcoming_sessions)} aula(s)",
        'metric_cards': [
            {
                **_build_metric_card('operation-kpi-card owner-emerald', 'Total de alunos', headline_metrics['students']),
                'status_hint': 'neutral',
                'href': reverse('student-directory'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-blue', 'Entradas abertas', headline_metrics['pending_intakes']),
                'status_hint': 'clean' if headline_metrics['pending_intakes'] == 0 else 'attention',
                'href': reverse('intake-center'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-whatsapp', 'WhatsApp pronto', headline_metrics['whatsapp_contacts']),
                'status_hint': 'neutral',
                'href': reverse('whatsapp-workspace'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-ruby', 'Cobrancas atrasadas', headline_metrics['overdue_payments']),
                'status_hint': 'clean' if headline_metrics['overdue_payments'] == 0 else 'attention',
                'href': reverse('finance-center'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-ruby', 'Matriculas sem cobranca', headline_metrics['ghost_enrollments']),
                'status_hint': 'clean' if headline_metrics['ghost_enrollments'] == 0 else 'danger',
                'href': reverse('finance-center'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-beacon', 'Red Beacon', red_beacon_snapshot['signal_mesh']['total_due_backlog']),
                'status_hint': 'attention' if red_beacon_snapshot['signal_mesh']['total_due_backlog'] > 0 else 'clean',
                'note': red_beacon_snapshot['summary'],
                'href': reverse('whatsapp-workspace'),
            },
        ],
        'owner_decision_entry_context': owner_decision_entry_context,
        'owner_operational_focus': owner_operational_focus,
        'red_beacon_snapshot': red_beacon_snapshot,
        'transport_payload': transport_payload,
    }
