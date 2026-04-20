"""
ARQUIVO: corredor de leitura do workspace de recepcao.

POR QUE ELE EXISTE:
- tira de `operations/queries.py` o bloco de recepcao que mistura fila, cobranca curta e leitura operacional.

O QUE ESTE ARQUIVO FAZ:
1. monta o core da recepcao com intakes, fila de cobranca e proximas aulas.
2. calcula sinais curtos de foco do balcao.
3. fecha o snapshot e o transport payload da recepcao.

PONTOS CRITICOS:
- preservar o bulk lookup de WhatsApp e a leitura de ownership de follow-up.
- manter o payload da recepcao estavel durante a extracao.
"""

from datetime import timedelta
from urllib.parse import quote

from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from communications.model_definitions.whatsapp import MessageDirection, WhatsAppMessageLog
from finance.models import Payment, PaymentMethod, PaymentStatus
from finance.overdue_metrics import get_overdue_payments_queryset
from onboarding.queries import get_pending_intakes
from operations.models import ClassSession
from shared_support.operational_contact_memory import (
    CONTACT_OWNERSHIP_MANAGER_OWNER,
    FINANCE_CONTACT_ACTIONS,
    ROLE_LABELS,
    TEAM_CONTACT_ROLE_SLUGS,
)
from shared_support.operational_settings import get_operational_whatsapp_repeat_block_hours
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


def _build_hero_stat(label, value):
    return {'label': label, 'value': value}


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


def _format_contact_history_timestamp(value):
    return timezone.localtime(value).strftime('%d/%m %H:%M')


def _extract_contact_subject_id(event, subject_type):
    metadata = event.metadata or {}
    metadata_subject_type = metadata.get('subject_type')
    if metadata_subject_type == subject_type and metadata.get('subject_id'):
        return str(metadata.get('subject_id'))
    if event.target_id:
        return str(event.target_id)
    return ''


def _build_latest_contact_event_map(*, subject_type, subject_ids, actions, actor_roles=None, since=None):
    normalized_ids = {str(subject_id) for subject_id in subject_ids if subject_id is not None}
    if not normalized_ids:
        return {}
    queryset = AuditEvent.objects.select_related('actor').filter(action__in=actions).order_by('-created_at')
    target_model_map = {
        'payment': 'payment',
        'intake': 'studentintake',
    }
    target_model = target_model_map.get(subject_type)
    if target_model:
        queryset = queryset.filter(target_model=target_model)
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)
    if actor_roles:
        queryset = queryset.filter(actor_role__in=actor_roles)

    event_map = {}
    for event in queryset:
        subject_id = _extract_contact_subject_id(event, subject_type)
        if not subject_id or subject_id not in normalized_ids or subject_id in event_map:
            continue
        event_map[subject_id] = event
        if len(event_map) == len(normalized_ids):
            break
    return event_map


def _serialize_reception_intake(intake):
    return {
        'id': intake.id,
        'full_name': intake.full_name,
        'phone': intake.phone,
        'email': getattr(intake, 'email', ''),
        'source_label': intake.get_source_display(),
        'status_label': intake.get_status_display(),
        'student_quick_create_href': (
            f"{reverse('student-quick-create')}"
            f"?intake={intake.id}"
            f"&context=reception-intake"
            f"&return_to={quote('/operacao/recepcao/#reception-intake-board')}"
            f"#student-form-essential"
        ),
    }


def _serialize_reception_session(session):
    attendance_count = len(list(session.attendances.all()))
    return {
        'id': session.id,
        'title': session.title,
        'scheduled_at': session.scheduled_at,
        'notes': session.notes,
        'attendance_count': attendance_count,
    }


def _build_reception_payment_reason(payment, *, today):
    if payment.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE] and payment.due_date < today:
        delay_days = max((today - payment.due_date).days, 0)
        return f'Pagamento vencido há {delay_days} dia(s) e já pede abordagem curta no balcão.'
    if payment.status == PaymentStatus.PENDING and payment.due_date == today:
        return 'Pagamento vence hoje e pode ser resolvido no próprio atendimento.'
    if payment.status == PaymentStatus.PENDING and payment.due_date > today:
        return f'Pagamento vence em {(payment.due_date - today).days} dia(s) e pode ser antecipado durante a passagem pelo caixa.'
    return 'Pagamento pede leitura operacional antes de escalar para o financeiro completo.'


def _build_reception_focus_signal(*, count, active_class):
    has_volume = (count or 0) > 0
    return {
        'severity_class': active_class if has_volume else 'severity-tranquil',
        'is_tranquil': not has_volume,
    }


def _build_reception_workspace_core(*, today):
    pending_intakes = list(get_pending_intakes(limit=6))
    payment_queue = list(
        Payment.objects.select_related('student', 'enrollment__plan')
        .filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE])
        .order_by('due_date')[:4]
    )
    overdue_payments_queryset = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    next_sessions = list(
        ClassSession.objects.filter(scheduled_at__date__gte=today)
        .prefetch_related('attendances')
        .order_by('scheduled_at')[:6]
    )
    active_students = Student.objects.count()
    overdue_payments = overdue_payments_queryset.count()
    due_today = sum(1 for payment in payment_queue if payment.status == PaymentStatus.PENDING and payment.due_date == today)
    first_intake = pending_intakes[0] if pending_intakes else None
    first_payment = payment_queue[0] if payment_queue else None
    next_session = next_sessions[0] if next_sessions else None

    repeat_block_hours = get_operational_whatsapp_repeat_block_hours()
    student_ids = [payment.student_id for payment in payment_queue]
    recent_cutoff = timezone.now() - timedelta(hours=repeat_block_hours) if repeat_block_hours > 0 else None

    all_outbound_logs = list(
        WhatsAppMessageLog.objects.filter(
            contact__linked_student_id__in=student_ids,
            direction=MessageDirection.OUTBOUND,
        ).values('contact__linked_student_id', 'created_at')
    )

    latest_finance_touch_map = _build_latest_contact_event_map(
        subject_type='payment',
        subject_ids=[payment.id for payment in payment_queue],
        actions=FINANCE_CONTACT_ACTIONS,
        actor_roles=TEAM_CONTACT_ROLE_SLUGS,
    )

    log_stats_map = {}
    for log in all_outbound_logs:
        student_id = log['contact__linked_student_id']
        if student_id not in log_stats_map:
            log_stats_map[student_id] = {'total': 0, 'recent': 0}
        log_stats_map[student_id]['total'] += 1
        if recent_cutoff and log['created_at'] >= recent_cutoff:
            log_stats_map[student_id]['recent'] += 1

    reception_payment_queue = []
    for payment in payment_queue:
        days_overdue = max((today - payment.due_date).days, 0)
        clean_phone = ''.join(filter(str.isdigit, payment.student.phone or ''))
        if clean_phone and not clean_phone.startswith('55'):
            clean_phone = f'55{clean_phone}'

        is_whatsapp_locked = False
        sent_count = 0
        if clean_phone:
            stats = log_stats_map.get(payment.student.id, {'total': 0, 'recent': 0})
            sent_count = stats['total']
            is_whatsapp_locked = stats['recent'] > 0

        latest_touch_event = latest_finance_touch_map.get(str(payment.id))
        latest_touch_metadata = latest_touch_event.metadata if latest_touch_event else {}
        is_manager_owned_follow_up = (
            latest_touch_metadata.get('ownership_scope') == CONTACT_OWNERSHIP_MANAGER_OWNER
            and bool(latest_touch_event)
        )
        contact_owner_hint = ''
        if is_manager_owned_follow_up:
            role_label = ROLE_LABELS.get(getattr(latest_touch_event, 'actor_role', ''), 'Equipe')
            contact_owner_hint = (
                f'Primeiro toque já feito por {role_label.lower()} em {_format_contact_history_timestamp(latest_touch_event.created_at)}.'
            )

        student_edit_href = reverse('student-quick-update', args=[payment.student.id])
        reception_payment_queue.append(
            {
                'payment_id': payment.id,
                'student_id': payment.student.id,
                'student_name': payment.student.full_name,
                'plan_name': payment.enrollment.plan.name if payment.enrollment and payment.enrollment.plan else 'Sem plano vinculado',
                'status_label': payment.get_status_display(),
                'status_class': 'warning' if payment.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE] else 'info',
                'due_date': payment.due_date,
                'amount': payment.amount,
                'method': payment.method,
                'method_label': payment.get_method_display(),
                'reference': payment.reference,
                'notes': payment.notes,
                'reason': _build_reception_payment_reason(payment, today=today),
                'student_href': student_edit_href,
                'clean_phone': clean_phone,
                'is_late_10_days': days_overdue >= 10,
                'is_whatsapp_locked': is_whatsapp_locked,
                'is_reception_blocked': sent_count >= 2,
                'is_manager_owned_follow_up': is_manager_owned_follow_up,
                'contact_owner_hint': contact_owner_hint,
                'repeat_block_hours': repeat_block_hours,
            }
        )

    return {
        'pending_intakes': pending_intakes,
        'payment_queue': payment_queue,
        'next_sessions': next_sessions,
        'first_intake': first_intake,
        'first_payment': first_payment,
        'next_session': next_session,
        'active_students': active_students,
        'overdue_payments': overdue_payments,
        'due_today': due_today,
        'hero_stats': [
            _build_hero_stat('Entradas', len(pending_intakes)),
            _build_hero_stat('Atrasos', overdue_payments),
            _build_hero_stat('Vence hoje', due_today),
            _build_hero_stat('Próximas aulas', len(next_sessions)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card manager-coral', 'Chegadas na fila', len(pending_intakes)),
            _build_metric_card('operation-kpi-card manager-gold', 'Caixa curto', len(payment_queue)),
            _build_metric_card('operation-kpi-card manager-sky', 'Base ativa', active_students),
            _build_metric_card('operation-kpi-card coach-indigo', 'Próximas aulas', len(next_sessions)),
        ],
        'payment_methods': list(PaymentMethod.choices),
        'queue': reception_payment_queue,
        'intakes': pending_intakes,
        'sessions': next_sessions,
    }


def build_reception_workspace_snapshot(*, today):
    data = _build_reception_workspace_core(today=today)
    first_intake = data['first_intake']
    first_payment = data['first_payment']
    next_session = data['next_session']
    reception_decision_entry_context = _build_decision_entry_context(
        {
            'key': 'intakes',
            'href': '#reception-intake-board',
            'href_label': 'Abrir fila',
            'label': 'Atenda primeiro',
            'summary': (
                f'{first_intake.full_name} abre a fila e mostra quem deve ser atendido primeiro no balcão.'
                if first_intake else
                'Sem entrada pendente agora. O balcão pode seguir para cobranças curtas e orientação de aulas.'
            ),
            'count': len(data['intakes']),
            'pill_class': 'warning' if first_intake else 'success',
        },
        {
            'key': 'payments',
            'href': '#reception-payment-board',
            'href_label': 'Abrir cobrança',
            'label': 'Resolver caixa curto',
            'summary': (
                f'{first_payment.student.full_name} aparece primeiro na fila curta de cobrança para resolver sem abrir o financeiro completo.'
                if first_payment else
                'Sem cobrança curta em fila agora. O atendimento pode seguir sem pressão financeira imediata.'
            ),
        },
    )
    snapshot_version = build_workspace_snapshot_version(
        {'key': 'intakes', 'items': data['intakes'], 'count': len(data['intakes'])},
        {'key': 'queue', 'items': data['queue'], 'count': len(data['queue'])},
        {'key': 'sessions', 'items': data['sessions'], 'count': len(data['sessions'])},
    )

    transport_payload = {
        'reception_queue': data['queue'],
        'reception_intakes': [_serialize_reception_intake(intake) for intake in data['intakes']],
        'reception_sessions': [_serialize_reception_session(session) for session in data['sessions']],
        'reception_payment_methods': [{'value': value, 'label': label} for value, label in data['payment_methods']],
    }
    return {
        'snapshot_version': snapshot_version,
        'hero_stats': data['hero_stats'],
        'metric_cards': data['metric_cards'],
        'reception_focus': [
            {
                **_build_reception_focus_signal(count=len(data['intakes']), active_class='severity-ruby'),
                'label': 'Atenda primeiro',
                'chip_label': 'Chegada',
                'summary': (
                    f'{first_intake.full_name} abre a fila e mostra quem deve ser atendido primeiro no balcão.'
                    if first_intake else
                    'Sem entrada pendente agora. O balcão pode seguir para cobranças curtas e orientação de aulas.'
                ),
                'count': len(data['intakes']),
                'pill_class': 'warning' if first_intake else 'success',
                'href': '#reception-intake-board',
                'href_label': 'Abrir fila',
            },
            {
                **_build_reception_focus_signal(count=len(data['queue']), active_class='severity-amber'),
                'label': 'Resolver caixa curto',
                'chip_label': 'Cobranças',
                'summary': (
                    f'{first_payment.student.full_name} aparece primeiro na fila curta de cobrança para resolver sem abrir o financeiro completo.'
                    if first_payment else
                    'Sem cobrança curta em fila agora. O atendimento pode seguir sem pressão financeira imediata.'
                ),
                'count': len(data['queue']),
                'pill_class': 'warning' if first_payment else 'info',
                'href': '#reception-payment-board',
                'href_label': 'Abrir cobrança',
            },
            {
                **_build_reception_focus_signal(count=len(data['sessions']), active_class='severity-cyan'),
                'label': 'Aulas do turno',
                'chip_label': 'Aulas',
                'summary': (
                    f'{next_session.title} é a próxima aula visível para orientar horário, coach e dúvida rápida no balcão.'
                    if next_session else
                    'Sem aula futura no recorte atual. A grade fica em leitura para orientar o atendimento quando preciso.'
                ),
                'count': len(data['sessions']),
                'pill_class': 'accent',
                'href': '#reception-class-grid-board',
                'href_label': 'Ver próximas aulas',
            },
        ],
        'reception_decision_entry_context': reception_decision_entry_context,
        'reception_boundaries': [
            'A Recepção acolhe, localiza, cadastra e encaminha sem assumir o papel do manager.',
            'A grade aqui continua em leitura apenas: orientar o balcão não significa gerenciar a agenda.',
            'A cobrança curta resolve pagamento e ajuste simples sem abrir o centro financeiro completo.',
        ],
        'reception_payment_methods': data['payment_methods'],
        'reception_queue': data['queue'],
        'reception_intakes': data['intakes'],
        'reception_sessions': data['sessions'],
        'transport_payload': transport_payload,
    }
