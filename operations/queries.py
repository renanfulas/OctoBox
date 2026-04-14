"""
ARQUIVO: snapshots de leitura do workspace operacional.

POR QUE ELE EXISTE:
- concentra a leitura operacional por papel fora de boxcore.operations.

O QUE ESTE ARQUIVO FAZ:
1. monta snapshots de owner, dev, manager e coach.
2. preserva consultas reutilizaveis fora da camada HTTP.

PONTOS CRITICOS:
- mudancas aqui afetam a leitura operacional por papel e a performance dessas telas.
"""

from datetime import timedelta
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from auditing.models import AuditEvent
from communications.application.message_templates import build_operational_message_body
from communications.queries import (
    build_communications_headline_metrics,
    get_unlinked_whatsapp_contacts,
)
from finance.models import Payment, PaymentMethod, PaymentStatus
from finance.overdue_metrics import get_overdue_payments_queryset, sum_overdue_amount
from monitoring.manager_realtime_metrics import build_manager_realtime_metrics_snapshot
from monitoring.student_realtime_metrics import build_student_realtime_metrics_snapshot
from onboarding.models import IntakeStatus
from onboarding.queries import get_pending_intakes
from operations.models import BehaviorCategory, ClassSession
from operations.session_snapshots import serialize_class_session, sync_runtime_statuses
from shared_support.operational_contact_memory import (
    ACTION_LABELS,
    CONTACT_COOLDOWN_DAYS,
    CONTACT_HISTORY_LOOKBACK_DAYS,
    CONTACT_MEMORY_ACTIONS,
    CONTACT_OWNERSHIP_MANAGER_OWNER,
    CONTACT_OWNERSHIP_SHARED,
    CONTACT_STAGE_FIRST_TOUCH_OPENED,
    CONTACT_STAGE_FOLLOW_UP_ACTIVE,
    CONTACT_STAGE_UNREACHED,
    FINANCE_CONTACT_ACTIONS,
    INTAKE_CONTACT_ACTIONS,
    MANAGER_FINANCE_WHATSAPP_ACTION,
    ROLE_LABELS,
    SURFACE_LABELS,
    TEAM_CONTACT_ROLE_SLUGS,
    build_contact_subject_key,
    is_finance_contact_action,
    is_intake_contact_action,
)
from shared_support.phone_numbers import normalize_phone_number
from shared_support.workspace_snapshot_versions import build_workspace_snapshot_version
from students.models import Student


def _build_hero_stat(label, value):
    return {'label': label, 'value': value}


def _build_metric_card(card_class, eyebrow, value, note=None):
    card = {
        'card_class': card_class,
        'eyebrow': eyebrow,
        'display_value': value,
    }
    if note:
        card['note'] = note
    return card


def _with_fragment(url, fragment):
    return f'{url}{fragment}' if fragment else url


def _build_manager_decision_action(
    *,
    label,
    note,
    tone,
    kind,
    aria_label,
    href='',
    post_url='',
    is_urgent=False,
    opens_in_new_tab=False,
    message_preview='',
):
    return {
        'label': label,
        'note': note,
        'tone': tone,
        'kind': kind,
        'href': href,
        'post_url': post_url,
        'aria_label': aria_label,
        'is_urgent': is_urgent,
        'opens_in_new_tab': opens_in_new_tab,
        'message_preview': message_preview,
    }


def _build_whatsapp_deep_link(*, phone, message):
    normalized_phone = normalize_phone_number(phone)
    if not normalized_phone:
        return ''
    if len(normalized_phone) in (10, 11):
        normalized_phone = f'55{normalized_phone}'
    return f'https://wa.me/{normalized_phone}?text={quote(message)}'


def _build_manager_intake_whatsapp_action(*, intake, label, note, tone, is_urgent, action_kind):
    if not normalize_phone_number(getattr(intake, 'phone', '')):
        return _build_manager_decision_action(
            label=label,
            note=note,
            tone=tone,
            kind='link',
            href=_with_fragment(reverse('intake-center'), '#tab-intake-queue'),
            aria_label=f'{label} para {intake.full_name}',
            is_urgent=is_urgent,
        )
    return _build_manager_decision_action(
        label=label,
        note=note,
        tone=tone,
        kind='post',
        post_url=reverse('manager-intake-contact', args=[intake.id]),
        aria_label=f'Abrir contato recomendado para {intake.full_name}',
        is_urgent=is_urgent,
        opens_in_new_tab=True,
        message_preview=action_kind,
    )


def _build_manager_whatsapp_action(*, student, action_kind, payment=None, enrollment=None):
    first_name = (student.full_name or 'Aluno').split()[0]
    message_preview = build_operational_message_body(
        action_kind=action_kind,
        first_name=first_name,
        payment_due_date=getattr(payment, 'due_date', None),
        payment_amount=getattr(payment, 'amount', None),
        plan_name=getattr(getattr(enrollment, 'plan', None), 'name', None),
    )
    href = _build_whatsapp_deep_link(phone=getattr(student, 'phone', ''), message=message_preview)
    if not href:
        return None
    return {
        'label': 'WhatsApp',
        'aria_label': f'Abrir WhatsApp com mensagem sugerida para {student.full_name}',
        'message_preview': message_preview,
        'opens_in_new_tab': True,
        'action_kind': action_kind,
        'student_id': student.id,
        'payment_id': getattr(payment, 'id', None),
        'enrollment_id': getattr(enrollment, 'id', None),
        'href': href,
    }


def _format_contact_history_timestamp(value):
    return timezone.localtime(value).strftime('%d/%m %H:%M')


def _build_contact_event_queryset(*, since=None, actor=None):
    queryset = AuditEvent.objects.select_related('actor').filter(action__in=CONTACT_MEMORY_ACTIONS)
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)
    if actor is not None:
        queryset = queryset.filter(actor=actor)
    return queryset.order_by('-created_at')


def _extract_contact_subject_id(event, subject_type):
    metadata = event.metadata or {}
    metadata_subject_type = metadata.get('subject_type')
    if metadata_subject_type == subject_type and metadata.get('subject_id'):
        return str(metadata.get('subject_id'))
    if event.target_id:
        return str(event.target_id)
    return ''


def _build_recent_contact_subject_sets(*, actor):
    if actor is None:
        return set(), set()
    cutoff = timezone.now() - timedelta(days=CONTACT_COOLDOWN_DAYS)
    intake_ids = set()
    payment_ids = set()
    for event in _build_contact_event_queryset(since=cutoff, actor=actor):
        if is_intake_contact_action(event.action):
            subject_id = _extract_contact_subject_id(event, 'intake')
            if subject_id:
                intake_ids.add(subject_id)
        if is_finance_contact_action(event.action):
            subject_id = _extract_contact_subject_id(event, 'payment')
            if subject_id:
                payment_ids.add(subject_id)
    return intake_ids, payment_ids


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


def _build_manager_history_items(*, actor=None, events=None):
    if events is None and actor is None:
        return []
    items = []
    if events is None:
        cutoff = timezone.now() - timedelta(days=CONTACT_HISTORY_LOOKBACK_DAYS)
        events = list(_build_contact_event_queryset(since=cutoff, actor=actor)[:12])
    for event in events:
        metadata = event.metadata or {}
        board_key = metadata.get('board_key') or ''
        items.append(
            {
                'action_label': ACTION_LABELS.get(event.action, 'Acao operacional'),
                'surface_label': SURFACE_LABELS.get(board_key, 'Operacao'),
                'subject_label': metadata.get('subject_label') or event.target_label or 'Caso operacional',
                'subject_key': build_contact_subject_key(
                    metadata.get('subject_type') or 'unknown',
                    metadata.get('subject_id') or event.target_id or 'unknown',
                ),
                'timestamp_label': _format_contact_history_timestamp(event.created_at),
                'channel_label': 'WhatsApp' if metadata.get('channel') == 'whatsapp' else 'Fluxo interno',
                'description': event.description or '',
            }
        )
    return items


def _build_manager_history_events(*, actor):
    if actor is None:
        return []
    cutoff = timezone.now() - timedelta(days=CONTACT_HISTORY_LOOKBACK_DAYS)
    return list(_build_contact_event_queryset(since=cutoff, actor=actor)[:12])


def _build_team_touch_note(*, event, actor):
    if event is None:
        return ''
    actor_id = getattr(actor, 'id', None)
    if actor_id and getattr(event, 'actor_id', None) == actor_id:
        return ''
    metadata = event.metadata or {}
    role_label = ROLE_LABELS.get(getattr(event, 'actor_role', ''), 'Equipe')
    board_label = SURFACE_LABELS.get(metadata.get('board_key') or '', 'Operacao')
    return f'{role_label} abriu contato de {board_label.lower()} em {_format_contact_history_timestamp(event.created_at)}.'


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


def _decorate_operational_sessions(serialized_sessions):
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


def _build_manager_focus_item(
    *,
    key,
    label,
    summary,
    count,
    pill_class,
    href,
    href_label,
    chip_label,
    status_mode,
    priority_score,
):
    return {
        'key': key,
        'label': label,
        'chip_label': chip_label,
        'summary': summary,
        'count': count,
        'pill_class': pill_class,
        'href': href,
        'href_label': href_label,
        'status_mode': status_mode,
        'priority_score': priority_score,
        'is_clickable': (count or 0) > 0,
    }


def _build_manager_operational_focus(*, pending_intakes_count, unlinked_whatsapp_count, payments_without_enrollment_count, financial_alerts_count):
    links_count = unlinked_whatsapp_count + payments_without_enrollment_count
    has_intakes = pending_intakes_count > 0
    has_links = links_count > 0
    has_finance = financial_alerts_count > 0

    if has_intakes:
        priority_order = {'intake': 300, 'finance': 200, 'links': 100}
    elif has_finance:
        priority_order = {'finance': 300, 'links': 200, 'intake': 100}
    elif has_links:
        priority_order = {'links': 300, 'intake': 200, 'finance': 100}
    else:
        priority_order = {'intake': 300, 'finance': 200, 'links': 100}

    focus_items = [
        _build_manager_focus_item(
            key='intake',
            label='Entradas esfriando' if has_intakes else 'Fila sob controle',
            chip_label='Entradas',
            summary=(
                f'{pending_intakes_count} contato(s) ja chegaram e pedem triagem agora para nao virarem fila morta.'
                if has_intakes else
                'Nenhuma entrada pede triagem agora; a fila comercial esta limpa.'
            ),
            count=pending_intakes_count,
            pill_class='warning' if has_intakes else 'success',
            href='#manager-intake-board',
            href_label='Priorizar entradas' if has_intakes else 'Validar entradas',
            status_mode='act_now' if has_intakes else 'clean',
            priority_score=priority_order['intake'] + pending_intakes_count,
        ),
        _build_manager_focus_item(
            key='links',
            label='Vinculos quebrados' if has_links else 'Vinculos estaveis',
            chip_label='Vinculos',
            summary=(
                f'{unlinked_whatsapp_count} contato(s) e {payments_without_enrollment_count} cobranca(s) ainda estao soltos e escondem atrito estrutural na operacao.'
                if has_links else
                'Sem contato ou cobranca solta agora; a estrutura esta consistente.'
            ),
            count=links_count,
            pill_class='info' if has_links else 'success',
            href='#manager-link-board',
            href_label='Corrigir vinculos' if has_links else 'Checar vinculos',
            status_mode='watch' if has_links else 'clean',
            priority_score=priority_order['links'] + links_count,
        ),
        _build_manager_focus_item(
            key='finance',
            label='Receita em risco' if has_finance else 'Caixa estavel',
            chip_label='Cobranca',
            summary=(
                f'{financial_alerts_count} alerta(s) ja pedem acao para evitar atraso, evasao ou ruido no caixa.'
                if has_finance else
                'Nenhum alerta financeiro pressiona o caixa agora; a leitura esta estavel.'
            ),
            count=financial_alerts_count,
            pill_class='warning' if has_finance else 'success',
            href='#manager-finance-board',
            href_label='Atacar cobrancas' if has_finance else 'Revisar caixa',
            status_mode='act_now' if has_finance else 'clean',
            priority_score=priority_order['finance'] + financial_alerts_count,
        ),
    ]
    return sorted(focus_items, key=lambda item: item['priority_score'], reverse=True)


def _build_manager_priority_context_from_item(primary_item=None):
    primary_item = primary_item or {}
    primary_key = primary_item.get('key')
    status_mode = primary_item.get('status_mode')

    if primary_key == 'intake' and status_mode == 'act_now':
        return {
            'title': 'Triagem primeiro para nao deixar entrada esfriar.',
            'copy': 'A fila comercial tem demanda esperando resposta e deve abrir a leitura do manager.',
            'pill_label': 'Entradas',
            'pill_class': 'warning',
        }
    if primary_key == 'finance' and status_mode == 'act_now':
        return {
            'title': 'Receita pede acao antes de virar ruido no caixa.',
            'copy': 'Sem triagem pressionando mais forte, os alertas financeiros viram a camada dominante do turno.',
            'pill_label': 'Cobranca',
            'pill_class': 'warning',
        }
    if primary_key == 'links' and status_mode in ['watch', 'act_now']:
        return {
            'title': 'Corrija vinculos antes de empilhar excecoes.',
            'copy': 'Contato sem aluno e cobranca sem matricula escondem atrito estrutural que contamina o resto da operacao.',
            'pill_label': 'Vinculos',
            'pill_class': 'info',
        }
    return {
        'title': 'A mesa esta limpa para leitura de manutencao.',
        'copy': 'Sem pressao dominante, a gerencia pode validar a operacao com mais calma e menos reatividade.',
        'pill_label': 'Estavel',
        'pill_class': 'success',
    }


def _build_manager_board_content(
    *,
    pending_intakes_count,
    unlinked_whatsapp_count,
    payments_without_enrollment_count,
    financial_alerts_count,
    history_count,
    intake_cooldown_count=0,
    finance_cooldown_count=0,
    finance_team_touch_count=0,
):
    has_intakes = pending_intakes_count > 0
    has_links = unlinked_whatsapp_count > 0
    has_enrollment_gaps = payments_without_enrollment_count > 0
    has_finance = financial_alerts_count > 0

    return {
        'intake': {
            'key': 'intake',
            'status_mode': 'act_now' if has_intakes else 'clean',
            'header': {
                'eyebrow': 'Entradas',
                'title': 'Quem pede triagem agora' if has_intakes else 'Fila sob controle',
                'copy': (
                    'A primeira resposta destrava a fila e evita contato esfriando.'
                    if has_intakes else
                    'Sem nova entrada pressionando a triagem, a fila comercial segue limpa.'
                ),
                'context_note': (
                    f'{intake_cooldown_count} contato(s) ja receberam sua abordagem e voltam em ate 3 dias se seguirem sem resolver.'
                    if intake_cooldown_count else
                    ''
                ),
                'pill_label': f'{pending_intakes_count} item(ns)' if has_intakes else 'Base limpa',
                'pill_class': 'warning' if has_intakes else 'accent',
            },
            'empty': {
                'eyebrow': 'Entradas',
                'title': 'Nenhuma entrada pede triagem',
                'copy': 'A triagem inicial nao tem novo contato aguardando encaminhamento agora.',
                'badge': 'Base limpa',
                'badge_class': 'accent',
            },
        },
        'links': {
            'key': 'links',
            'status_mode': 'watch' if has_links else 'clean',
            'header': {
                'eyebrow': 'Vinculos',
                'title': 'Contatos ainda sem aluno' if has_links else 'Vinculos de contato estaveis',
                'copy': (
                    'Conversa solta vira atrito estrutural se ninguem conectar agora.'
                    if has_links else
                    'Nenhuma conversa pede conexao com aluno neste momento.'
                ),
                'pill_label': f'{unlinked_whatsapp_count} contato(s)' if has_links else 'Inbox organizado',
                'pill_class': 'info' if has_links else 'accent',
            },
            'empty': {
                'eyebrow': 'Vinculos',
                'title': 'Nenhum contato pendente',
                'copy': 'Nao ha conversa solta exigindo identificacao ou conexao com aluno agora.',
                'badge': 'Inbox organizado',
                'badge_class': 'info',
            },
        },
        'enrollment_links': {
            'key': 'enrollment_links',
            'status_mode': 'watch' if has_enrollment_gaps else 'clean',
            'header': {
                'eyebrow': 'Vinculos',
                'title': 'Cobrancas ainda sem matricula' if has_enrollment_gaps else 'Estrutura financeira coerente',
                'copy': (
                    'Resolva vencimentos mais proximos antes que o financeiro herde estrutura quebrada.'
                    if has_enrollment_gaps else
                    'Sem cobranca solta sem matricula, a base financeira segue coerente.'
                ),
                'pill_label': f'{payments_without_enrollment_count} pendencia(s)' if has_enrollment_gaps else 'Estrutura coerente',
                'pill_class': 'info' if has_enrollment_gaps else 'accent',
                'live_pill_label': 'Escuta pronta',
                'live_pill_class': 'neutral',
            },
            'empty': {
                'eyebrow': 'Vinculos',
                'title': 'Nenhum pagamento aguardando vinculo',
                'copy': 'A estrutura financeira nao tem cobranca solta sem matricula ativa neste recorte.',
                'badge': 'Estrutura coerente',
                'badge_class': 'accent',
            },
        },
        'finance': {
            'key': 'finance',
            'status_mode': 'act_now' if has_finance else 'clean',
            'header': {
                'eyebrow': 'Cobranca',
                'title': 'Onde a receita ja pede acao' if has_finance else 'Caixa sem pressao imediata',
                'copy': (
                    'Atraso, evasao e ruido no caixa comecam onde a cobranca fica sem resposta.'
                    if has_finance else
                    'Sem alerta pressionando o caixa, a gerencia pode revisar com calma operacional.'
                ),
                'context_note': (
                    f'{finance_team_touch_count} caso(s) ja tiveram primeiro toque da equipe e agora pedem follow-up de gerencia.'
                    if finance_team_touch_count else
                    f'{finance_cooldown_count} cobranca(s) ja receberam seu toque e voltam em ate 3 dias se seguirem abertas.'
                    if finance_cooldown_count else
                    ''
                ),
                'pill_label': f'{financial_alerts_count} alerta(s)' if has_finance else 'Carteira respirando',
                'pill_class': 'warning' if has_finance else 'accent',
                'live_pill_label': 'Escuta pronta',
                'live_pill_class': 'neutral',
            },
            'empty': {
                'eyebrow': 'Cobranca',
                'title': 'Nenhum alerta financeiro',
                'copy': 'A gerencia nao tem atraso ou cobranca pressionando acompanhamento agora.',
                'badge': 'Carteira respirando',
                'badge_class': 'accent',
            },
        },
        'history': {
            'key': 'history',
            'status_mode': 'watch' if history_count else 'clean',
            'header': {
                'eyebrow': 'Historico',
                'title': 'Pegadas da gerencia',
                'copy': (
                    'Veja as ultimas abordagens para nao repetir a mesma porta antes de trocar a estrategia.'
                    if history_count else
                    'As pegadas recentes da gerencia aparecerao aqui conforme os contatos forem acontecendo.'
                ),
                'pill_label': f'{history_count} acao(oes)' if history_count else '15 dias',
                'pill_class': 'info' if history_count else 'accent',
            },
            'empty': {
                'eyebrow': 'Historico',
                'title': 'Nenhuma pegada recente',
                'copy': 'Os ultimos 15 dias ainda nao registraram contato operacional feito por voce neste workspace.',
                'badge': '15 dias',
                'badge_class': 'accent',
            },
        },
    }


def _attach_manager_intake_decision(intake, *, is_priority):
    intake.contact_subject_key = build_contact_subject_key('intake', intake.id)
    status = getattr(intake, 'status', '')
    source = getattr(intake, 'source', '')

    if status == IntakeStatus.NEW:
        intake.decision_label = 'Responder agora' if is_priority else 'Puxar conversa'
        intake.decision_note = (
            'Lead novo no topo da fila; vale abrir o primeiro contato agora.'
            if is_priority else
            'Primeiro contato ainda pendente para tirar a entrada do estado frio.'
        )
        intake.decision_class = 'warning' if is_priority else 'info'
        intake.decision_action = _build_manager_intake_whatsapp_action(
            intake=intake,
            label=intake.decision_label,
            note=intake.decision_note,
            tone='urgent' if is_priority else 'preventive',
            is_urgent=is_priority,
            action_kind='intake-first-touch',
        )
        return intake

    if status == IntakeStatus.REVIEWING:
        intake.decision_label = 'Fechar conversa'
        intake.decision_note = (
            'Lead aquecido no WhatsApp e perto de virar aluno.'
            if source == 'whatsapp' else
            'Caso em revisao pede definicao para nao voltar para a fila fria.'
        )
        intake.decision_class = 'accent'
        intake.decision_action = _build_manager_intake_whatsapp_action(
            intake=intake,
            label=intake.decision_label,
            note=intake.decision_note,
            tone='structural' if source != 'whatsapp' else 'preventive',
            is_urgent=False,
            action_kind='intake-follow-up',
        )
        return intake

    intake.decision_label = 'Revisar caso'
    intake.decision_note = 'Use esta leitura para decidir se acelera, fecha ou limpa a fila.'
    intake.decision_class = 'info'
    intake.decision_action = _build_manager_intake_whatsapp_action(
        intake=intake,
        label=intake.decision_label,
        note=intake.decision_note,
        tone='preventive',
        is_urgent=False,
        action_kind='intake-follow-up',
    )
    return intake


def _attach_manager_link_decision(contact, *, is_priority):
    contact.contact_subject_key = build_contact_subject_key('contact', contact.id)
    has_name = bool(getattr(contact, 'display_name', ''))
    student_directory_href = reverse('student-directory')
    if has_name:
        contact.decision_label = 'Vincular agora' if is_priority else 'Vincular aluno'
        contact.decision_note = (
            'Contato identificado no topo da fila e pronto para conexao com aluno.'
            if is_priority else
            'A conversa ja tem identidade suficiente para sair do limbo estrutural.'
        )
        contact.decision_class = 'accent'
        contact.decision_action = _build_manager_decision_action(
            label=contact.decision_label,
            note=contact.decision_note,
            tone='urgent' if is_priority else 'structural',
            kind='link',
            href=student_directory_href,
            aria_label=f'{contact.decision_label} para {contact.display_name or contact.phone}',
            is_urgent=is_priority,
        )
        return contact

    contact.decision_label = 'Identificar agora' if is_priority else 'Identificar contato'
    contact.decision_note = 'Sem nome confiavel, o vinculo continua cego e contamina o restante da leitura.'
    contact.decision_class = 'warning'
    contact.decision_action = _build_manager_decision_action(
        label=contact.decision_label,
        note=contact.decision_note,
        tone='urgent' if is_priority else 'structural',
        kind='link',
        href=student_directory_href,
        aria_label=f'{contact.decision_label} para {contact.phone}',
        is_urgent=is_priority,
    )
    return contact


def _attach_manager_finance_decision(payment, *, today, is_priority, enrollment_required=False):
    payment.contact_subject_key = build_contact_subject_key('payment', payment.id)
    is_overdue = payment.status == PaymentStatus.OVERDUE or (
        payment.status == PaymentStatus.PENDING and payment.due_date < today
    )
    due_today = payment.status == PaymentStatus.PENDING and payment.due_date == today
    student_financial_href = _with_fragment(
        reverse('student-quick-update', args=[payment.student.id]),
        '#student-financial-overview',
    )

    if enrollment_required:
        payment.decision_label = 'Destravar hoje' if is_priority else 'Corrigir vinculo'
        payment.decision_note = (
            'Sem matricula ativa, a cobranca fica solta e distorce a leitura financeira.'
            if is_overdue or due_today else
            'Corrija o vinculo antes que o financeiro herde estrutura quebrada.'
        )
        payment.decision_class = 'warning' if (is_priority or is_overdue or due_today) else 'info'
        payment.decision_action = _build_manager_decision_action(
            label=payment.decision_label,
            note=payment.decision_note,
            tone='urgent' if (is_priority or is_overdue or due_today) else 'structural',
            kind='post',
            post_url=reverse('payment-enrollment-link', args=[payment.id]),
            aria_label=f'{payment.decision_label} para {payment.student.full_name}',
            is_urgent=(is_priority or is_overdue or due_today),
        )
        payment.whatsapp_action = None
        return payment

    if is_overdue:
        payment.decision_label = 'Cobrar hoje'
        payment.decision_note = 'Pagamento vencido ja pressiona caixa e retencao.'
        payment.decision_class = 'warning'
        payment.decision_action = _build_manager_decision_action(
            label=payment.decision_label,
            note=payment.decision_note,
            tone='urgent',
            kind='link',
            href=student_financial_href,
            aria_label=f'{payment.decision_label} de {payment.student.full_name}',
            is_urgent=True,
        )
        payment.whatsapp_action = _build_manager_whatsapp_action(
            student=payment.student,
            action_kind='overdue',
            payment=payment,
            enrollment=getattr(payment, 'enrollment', None),
        )
        return payment

    if due_today:
        payment.decision_label = 'Agir hoje'
        payment.decision_note = 'Pagamento vence hoje e cabe abordagem curta antes de virar atraso.'
        payment.decision_class = 'info'
        payment.decision_action = _build_manager_decision_action(
            label=payment.decision_label,
            note=payment.decision_note,
            tone='urgent',
            kind='link',
            href=student_financial_href,
            aria_label=f'{payment.decision_label} com {payment.student.full_name}',
            is_urgent=True,
        )
        payment.whatsapp_action = _build_manager_whatsapp_action(
            student=payment.student,
            action_kind='upcoming',
            payment=payment,
            enrollment=getattr(payment, 'enrollment', None),
        )
        return payment

    payment.decision_label = 'Prevenir atraso'
    payment.decision_note = 'Contato preventivo reduz ruido antes do vencimento.'
    payment.decision_class = 'accent'
    payment.decision_action = _build_manager_decision_action(
        label=payment.decision_label,
        note=payment.decision_note,
        tone='preventive',
        kind='link',
        href=student_financial_href,
        aria_label=f'{payment.decision_label} de {payment.student.full_name}',
        is_urgent=False,
    )
    payment.whatsapp_action = _build_manager_whatsapp_action(
        student=payment.student,
        action_kind='upcoming',
        payment=payment,
        enrollment=getattr(payment, 'enrollment', None),
    )
    return payment


def build_owner_workspace_snapshot(*, today):
    communications_metrics = build_communications_headline_metrics(today=today)
    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    overdue_amount = sum_overdue_amount(Payment.objects.all(), today=today)
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
            label='Ver cobrancas',
        chip_label='Cobrança',
            summary=(
                f"{headline_metrics['overdue_payments']} cobranca(s) estao atrasadas e pedem contato."
                if headline_metrics['overdue_payments']
                else 'Nenhuma cobranca atrasada pede contato agora.'
            ),
            count=headline_metrics['overdue_payments'],
            pill_class='danger' if headline_metrics['overdue_payments'] > 0 else 'success',
            href=reverse('finance-center'),
            href_label='Abrir cobrancas',
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
    }
    if headline_metrics['pending_intakes'] > 0:
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
    )
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
        ],
        'owner_decision_entry_context': owner_decision_entry_context,
        'owner_operational_focus': owner_operational_focus,
    }


def build_dev_workspace_snapshot():
    technical_metrics = {
        'eventos_auditados': AuditEvent.objects.count(),
        'eventos_24h': AuditEvent.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count(),
        'usuarios_com_papel': get_user_model().objects.filter(groups__isnull=False).distinct().count(),
    }
    student_realtime_metrics = build_student_realtime_metrics_snapshot()
    manager_realtime_metrics = build_manager_realtime_metrics_snapshot()
    recent_audit_events = list(AuditEvent.objects.select_related('actor')[:10])
    return {
        'technical_metrics': technical_metrics,
        'student_realtime_metrics': student_realtime_metrics,
        'manager_realtime_metrics': manager_realtime_metrics,
        'hero_stats': [
            _build_hero_stat('Auditados', technical_metrics['eventos_auditados']),
            _build_hero_stat('Ultimas 24h', technical_metrics['eventos_24h']),
            _build_hero_stat('Usuarios', technical_metrics['usuarios_com_papel']),
            _build_hero_stat('Realtime', student_realtime_metrics['events_total']),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card dev-steel', 'Eventos auditados', technical_metrics['eventos_auditados'], 'Historico total sensivel disponivel para investigacao, leitura forense e prova operacional.'),
            _build_metric_card('operation-kpi-card dev-cyan', 'Eventos nas ultimas 24h', technical_metrics['eventos_24h'], 'Volume recente para avaliar movimentacao real e detectar ondas anormais de alteracao.'),
            _build_metric_card('operation-kpi-card dev-emerald', 'Usuarios com papel', technical_metrics['usuarios_com_papel'], 'Cobertura atual de contas com fronteira operacional definida no sistema.'),
            _build_metric_card('operation-kpi-card dev-cyan', 'Eventos realtime', student_realtime_metrics['events_total'], 'Sinais SSE publicados para locks, financeiro, matricula e perfil do drawer de alunos.'),
            _build_metric_card('operation-kpi-card dev-steel', 'Streams ativos', student_realtime_metrics['active_streams'], 'Conexoes SSE vivas neste instante para observar concorrencia sem polling cego.'),
            _build_metric_card('operation-kpi-card dev-emerald', 'Conflitos de save', student_realtime_metrics['conflicts_total'], 'Tentativas bloqueadas por versao velha em vez de sobrescrever dado novo.'),
        ],
        'dev_operational_focus': [
            {
                'label': 'Comece pelo rastro recente',
                'chip_label': 'Auditoria',
                'summary': f"{technical_metrics['eventos_24h']} evento(s) nas ultimas 24h mostram se a investigacao deve comecar no agora ou no historico amplo.",
                'pill_class': 'warning' if technical_metrics['eventos_24h'] > 0 else 'success',
                'href': '#dev-audit-board',
                'href_label': 'Ver eventos recentes',
            },
            {
                'label': 'Depois valide a cobertura de acesso',
                'chip_label': 'Fronteiras',
                'summary': f"{technical_metrics['usuarios_com_papel']} usuario(s) com papel ajudam a medir se a fronteira operacional continua coerente.",
                'pill_class': 'info',
                'href': '#dev-boundary-board',
                'href_label': 'Ver fronteiras',
            },
            {
                'label': 'Feche com leitura sistemica',
                'chip_label': 'Rastros',
                'summary': f"{technical_metrics['eventos_auditados']} rastro(s) auditado(s) sustentam manutencao, investigacao e prova operacional sem virar chute tecnico.",
                'pill_class': 'accent',
                'href': '#dev-read-board',
                'href_label': 'Ver trilha curta',
            },
        ],
        'recent_audit_events': recent_audit_events,
        'dev_boundaries': [
            {
                'title': 'DEV investiga sem assumir a operacao',
                'copy': 'O papel tecnico mantem o sistema e investiga rastros, mas nao deve virar manager, recepcao ou coach por atalho.',
            },
            {
                'title': 'Leitura ampla, escrita minima',
                'copy': 'Quando houver manutencao, o caminho seguro e operar com rastreabilidade e o menor alcance de escrita necessario.',
            },
            {
                'title': 'Contingencia nao e rotina',
                'copy': 'Acesso elevado de emergencia fica fora do fluxo diario e precisa nascer com regra propria antes de existir.',
            },
        ],
        'dev_reads': [
            {
                'title': 'Mapa do sistema antes do mergulho',
                'copy': 'Comece pela arquitetura e pelo fluxo principal para nao investigar sintoma como se fosse causa raiz.',
            },
            {
                'title': 'Papeis e acessos como segunda camada',
                'copy': 'Revise as fronteiras de permissao antes de concluir que o problema esta na interface ou no dado.',
            },
            {
                'title': 'Auditoria por ultimo no recorte certo',
                'copy': 'Abra a trilha sensivel para confirmar ator, horario e alvo sem depender de memoria tecnica ou conversa paralela.',
            },
        ],
        'dev_table_guides': [
            {
                'title': 'Rastro que deve abrir a investigacao',
                'eyebrow': f"{technical_metrics['eventos_24h']} evento(s) nas ultimas 24h",
                'copy': 'Comece por aqui quando precisar localizar alteracao recente antes de abrir historico inteiro e perder tempo tecnico.',
            },
            {
                'title': 'Cobertura de fronteira atual',
                'eyebrow': f"{technical_metrics['usuarios_com_papel']} usuario(s) com papel",
                'copy': 'Use este ponto para validar se acesso continua com dono claro ou se alguma conta ja saiu da fronteira prevista.',
            },
            {
                'title': 'Base forense disponivel',
                'eyebrow': f"{technical_metrics['eventos_auditados']} rastro(s) auditado(s)",
                'copy': 'Esse volume sustenta manutencao e prova operacional sem depender de memoria tecnica, conversa paralela ou chute.',
            },
        ],
    }


def build_manager_workspace_snapshot(*, actor=None):
    today = timezone.localdate()
    cooldown_intake_ids, cooldown_payment_ids = _build_recent_contact_subject_sets(actor=actor)

    pending_intakes_pool = list(get_pending_intakes(limit=24))
    intake_cooldown_count = sum(1 for intake in pending_intakes_pool if str(intake.id) in cooldown_intake_ids)
    pending_intakes = [
        intake
        for intake in pending_intakes_pool
        if str(intake.id) not in cooldown_intake_ids
    ][:8]
    for index, intake in enumerate(pending_intakes):
        _attach_manager_intake_decision(intake, is_priority=(index == 0))

    unlinked_whatsapp = list(get_unlinked_whatsapp_contacts(limit=8))
    for index, contact in enumerate(unlinked_whatsapp):
        _attach_manager_link_decision(contact, is_priority=(index == 0))

    financial_alerts_pool = [
        payment
        for payment in Payment.objects.select_related('student').filter(
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]
        ).order_by('due_date')[:24]
    ]
    finance_cooldown_count = sum(1 for payment in financial_alerts_pool if str(payment.id) in cooldown_payment_ids)
    financial_alerts = [
        payment
        for payment in financial_alerts_pool
        if str(payment.id) not in cooldown_payment_ids
    ][:8]
    for index, payment in enumerate(financial_alerts):
        _attach_manager_finance_decision(payment, today=today, is_priority=(index == 0))

    payments_without_enrollment = list(Payment.objects.select_related('student').filter(
        enrollment__isnull=True,
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
    ).order_by('due_date')[:8])
    for index, payment in enumerate(payments_without_enrollment):
        _attach_manager_finance_decision(payment, today=today, is_priority=(index == 0), enrollment_required=True)

    finance_touch_cutoff = timezone.now() - timedelta(days=CONTACT_HISTORY_LOOKBACK_DAYS)
    latest_finance_touch_map = _build_latest_contact_event_map(
        subject_type='payment',
        subject_ids=[payment.id for payment in financial_alerts],
        actions=FINANCE_CONTACT_ACTIONS,
        actor_roles=TEAM_CONTACT_ROLE_SLUGS,
        since=finance_touch_cutoff,
    )
    for payment in financial_alerts:
        latest_touch_event = latest_finance_touch_map.get(str(payment.id))
        payment.team_touch_label = ''
        if latest_touch_event and getattr(latest_touch_event, 'actor_role', '') in {ROLE_RECEPTION, ROLE_OWNER}:
            role_label = ROLE_LABELS.get(getattr(latest_touch_event, 'actor_role', ''), 'Equipe')
            payment.team_touch_label = f'1o toque pela {role_label.lower()}'
        payment.team_touch_note = _build_team_touch_note(
            event=latest_touch_event,
            actor=actor,
        )
    finance_team_touch_count = sum(1 for payment in financial_alerts if getattr(payment, 'team_touch_label', ''))

    manager_history_events = _build_manager_history_events(actor=actor)
    manager_recent_history = _build_manager_history_items(events=manager_history_events)
    manager_operational_focus = _build_manager_operational_focus(
        pending_intakes_count=len(pending_intakes),
        unlinked_whatsapp_count=len(unlinked_whatsapp),
        payments_without_enrollment_count=len(payments_without_enrollment),
        financial_alerts_count=len(financial_alerts),
    )
    manager_board_content = _build_manager_board_content(
        pending_intakes_count=len(pending_intakes),
        unlinked_whatsapp_count=len(unlinked_whatsapp),
        payments_without_enrollment_count=len(payments_without_enrollment),
        financial_alerts_count=len(financial_alerts),
        history_count=len(manager_recent_history),
        intake_cooldown_count=intake_cooldown_count,
        finance_cooldown_count=finance_cooldown_count,
        finance_team_touch_count=finance_team_touch_count,
    )
    manager_primary_focus = manager_operational_focus[0] if manager_operational_focus else {}
    manager_secondary_focus = manager_operational_focus[1] if len(manager_operational_focus) > 1 else {}
    manager_priority_context = _build_manager_priority_context_from_item(manager_primary_focus)
    manager_decision_entry_context = _build_decision_entry_context(
        manager_primary_focus,
        manager_secondary_focus,
    )
    snapshot_version = build_workspace_snapshot_version(
        {'key': 'intakes', 'items': pending_intakes_pool, 'count': len(pending_intakes_pool)},
        {'key': 'links', 'items': unlinked_whatsapp, 'count': len(unlinked_whatsapp)},
        {'key': 'finance', 'items': financial_alerts_pool, 'count': len(financial_alerts_pool)},
        {'key': 'enrollment_links', 'items': payments_without_enrollment, 'count': len(payments_without_enrollment)},
        {'key': 'history', 'items': manager_history_events, 'count': len(manager_history_events)},
    )
    return {
        'snapshot_version': snapshot_version,
        'pending_intakes': pending_intakes,
        'unlinked_whatsapp': unlinked_whatsapp,
        'financial_alerts': financial_alerts,
        'payments_without_enrollment': payments_without_enrollment,
        'manager_priority_surface': manager_primary_focus.get('key', 'intake'),
        'manager_priority_context': manager_priority_context,
        'manager_decision_entry_context': manager_decision_entry_context,
        'manager_board_content': manager_board_content,
        'manager_recent_history': manager_recent_history,
        'hero_stats': [
            _build_hero_stat('Entradas', len(pending_intakes)),
            _build_hero_stat('WhatsApp', len(unlinked_whatsapp)),
            _build_hero_stat('Sem vinculo', len(payments_without_enrollment)),
            _build_hero_stat('Alertas', len(financial_alerts)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card manager-coral', 'Entradas pendentes', len(pending_intakes)),
            _build_metric_card('operation-kpi-card manager-sky', 'Contatos sem vinculo', len(unlinked_whatsapp)),
            _build_metric_card('operation-kpi-card manager-gold', 'Pagamentos sem matricula', len(payments_without_enrollment)),
            _build_metric_card('operation-kpi-card manager-steel', 'Alertas financeiros', len(financial_alerts)),
        ],
        'manager_operational_focus': manager_operational_focus,
    }


def build_coach_workspace_snapshot(*, today):
    sessions = (
        ClassSession.objects.filter(scheduled_at__date=today)
        .prefetch_related('attendances__student')
        .annotate(attendance_cnt=Count('attendances'))
        .order_by('scheduled_at')
    )
    total_attendances = sum(session.attendance_cnt for session in sessions)
    sessions_with_students = sum(1 for session in sessions if session.attendance_cnt > 0)
    pending_checkins = sum(max(session.attendance_cnt, 0) for session in sessions)
    coach_decision_entry_context = _build_decision_entry_context(
        {
            'key': 'sessions',
            'href': '#coach-sessions-board',
            'href_label': 'Ver aulas do dia',
            'label': 'Comece pela agenda de hoje',
            'summary': f'{len(sessions)} aula(s) definem o turno e mostram se o coach entra em dia cheio ou leitura leve.',
            'count': len(sessions),
            'pill_class': 'info' if len(sessions) > 0 else 'success',
        },
        {
            'key': 'boundaries',
            'href': '#coach-boundary-board',
            'href_label': 'Ver limites da área',
            'label': 'Feche com ocorrências técnicas',
            'summary': f'{len(BehaviorCategory.choices)} categoria(s) cobrem o registro técnico sem misturar treino com financeiro ou recepção.',
        },
    )
    return {
        'sessions_today': sessions,
        'hero_stats': [
            _build_hero_stat('Aulas', len(sessions)),
            _build_hero_stat('Rotinas', 3),
            _build_hero_stat('Limites', 3),
            _build_hero_stat('Ocorrencias', len(BehaviorCategory.choices)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card coach-mint', 'Aulas do dia', len(sessions)),
            _build_metric_card('operation-kpi-card coach-indigo', 'Alunos na lista', total_attendances),
            _build_metric_card('operation-kpi-card coach-orange', 'Check-ins no turno', sessions_with_students),
            _build_metric_card('operation-kpi-card coach-orange', 'Pendencias de check-in', pending_checkins),
        ],
        'coach_operational_focus': [
            {
                'label': 'Comece pela agenda de hoje',
                'chip_label': 'Turmas',
                'summary': f'{len(sessions)} aula(s) definem o turno e mostram se o coach entra em dia cheio ou leitura leve.',
                'count': len(sessions),
                'pill_class': 'info' if len(sessions) > 0 else 'success',
                'href': '#coach-sessions-board',
                'href_label': 'Ver aulas do dia',
            },
            {
                'label': 'Depois veja onde ja ha presenca real',
                'chip_label': 'Presenca',
                'summary': f'{sessions_with_students} turma(s) ja tem lista ativa e {total_attendances} presenca(s) para registrar sem ruido administrativo.',
                'count': sessions_with_students,
                'pill_class': 'accent',
                'href': '#coach-sessions-board',
                'href_label': 'Abrir rotina de presenca',
            },
        ],
        'coach_decision_entry_context': coach_decision_entry_context,
        'behavior_categories': BehaviorCategory.choices,
    }


def _build_reception_payment_reason(payment, *, today):
    if payment.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE] and payment.due_date < today:
        delay_days = max((today - payment.due_date).days, 0)
        return f'Pagamento vencido ha {delay_days} dia(s) e ja pede abordagem curta de balcao.'
    if payment.status == PaymentStatus.PENDING and payment.due_date == today:
        return 'Pagamento vence hoje e pode ser resolvido no proprio atendimento.'
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

    from django.utils import timezone
    from datetime import timedelta
    from shared_support.operational_settings import get_operational_whatsapp_repeat_block_hours
    from communications.model_definitions.whatsapp import WhatsAppMessageLog, MessageDirection
    
    repeat_block_hours = get_operational_whatsapp_repeat_block_hours()
    
    # AAA Performance AAA (Ghost Hardening): Bulk WhatsApp Log Pre-fetch
    # Buscamos todos os logs relevantes da fila inteira em uma tacada so.
    student_ids = [p.student_id for p in payment_queue]
    recent_cutoff = timezone.now() - timedelta(hours=repeat_block_hours) if repeat_block_hours > 0 else None
    
    all_outbound_logs = list(WhatsAppMessageLog.objects.filter(
        contact__linked_student_id__in=student_ids,
        direction=MessageDirection.OUTBOUND
    ).values('contact__linked_student_id', 'created_at'))

    latest_finance_touch_map = _build_latest_contact_event_map(
        subject_type='payment',
        subject_ids=[payment.id for payment in payment_queue],
        actions=FINANCE_CONTACT_ACTIONS,
        actor_roles=TEAM_CONTACT_ROLE_SLUGS,
    )
    
    # Agrupamos por aluno para busca O(1) no loop
    log_stats_map = {}
    for log in all_outbound_logs:
        s_id = log['contact__linked_student_id']
        if s_id not in log_stats_map:
            log_stats_map[s_id] = {'total': 0, 'recent': 0}
        log_stats_map[s_id]['total'] += 1
        if recent_cutoff and log['created_at'] >= recent_cutoff:
            log_stats_map[s_id]['recent'] += 1

    reception_payment_queue = []
    for payment in payment_queue:
        days_overdue = max((today - payment.due_date).days, 0)
        clean_phone = "".join(filter(str.isdigit, payment.student.phone or ''))
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
                f'Primeiro toque ja feito por {role_label.lower()} em {_format_contact_history_timestamp(latest_touch_event.created_at)}.'
            )

        student_edit_href = reverse('student-quick-update', args=[payment.student.id])
        reception_payment_queue.append({
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
        })

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
            _build_hero_stat('Aulas proximas', len(next_sessions)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card manager-coral', 'Entradas prontas', len(pending_intakes)),
            _build_metric_card('operation-kpi-card manager-gold', 'Cobrancas curtas', len(payment_queue)),
            _build_metric_card('operation-kpi-card manager-sky', 'Base alcancada', active_students),
            _build_metric_card('operation-kpi-card coach-indigo', 'Proximas aulas', len(next_sessions)),
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
            'href_label': 'Ver entradas',
            'label': 'Comece por quem acabou de chegar',
            'summary': (
                f'{first_intake.full_name} abre a fila e mostra o melhor ponto para acolher, localizar e converter sem esfriar o atendimento.'
                if first_intake else
                'Sem entrada pendente agora, entao o balcao pode priorizar caixa curto e orientacao de aulas.'
            ),
            'count': len(data['intakes']),
            'pill_class': 'warning' if first_intake else 'success',
        },
        {
            'key': 'payments',
            'href': '#reception-payment-board',
            'href_label': 'Ver cobranca curta',
            'label': 'Depois resolva o caixa curto',
            'summary': (
                f'{first_payment.student.full_name} aparece primeiro na fila e ajuda a validar se a cobranca esta clara o suficiente para ser resolvida no balcao.'
                if first_payment else
                'Sem cobranca curta em fila agora, entao o atendimento pode seguir sem pressao financeira imediata.'
            ),
        },
    )
    snapshot_version = build_workspace_snapshot_version(
        {'key': 'intakes', 'items': data['intakes'], 'count': len(data['intakes'])},
        {'key': 'queue', 'items': data['queue'], 'count': len(data['queue'])},
        {'key': 'sessions', 'items': data['sessions'], 'count': len(data['sessions'])},
    )

    return {
        'snapshot_version': snapshot_version,
        'hero_stats': data['hero_stats'],
        'metric_cards': data['metric_cards'],
        'reception_focus': [
            {
                **_build_reception_focus_signal(count=len(data['intakes']), active_class='severity-ruby'),
                'label': 'Comece por quem acabou de chegar',
                'chip_label': 'Chegada',
                'summary': (
                    f'{first_intake.full_name} abre a fila e mostra o melhor ponto para acolher, localizar e converter sem esfriar o atendimento.'
                    if first_intake else
                    'Sem entrada pendente agora, entao o balcao pode priorizar caixa curto e orientacao de aulas.'
                ),
                'count': len(data['intakes']),
                'pill_class': 'warning' if first_intake else 'success',
                'href': '#reception-intake-board',
                'href_label': 'Ver entradas',
            },
            {
                **_build_reception_focus_signal(count=len(data['queue']), active_class='severity-amber'),
                'label': 'Depois resolva o caixa curto',
                'chip_label': 'Cobrancas',
                'summary': (
                    f'{first_payment.student.full_name} aparece primeiro na fila e ajuda a validar se a cobranca esta clara o suficiente para ser resolvida no balcao.'
                    if first_payment else
                    'Sem cobranca curta em fila agora, entao o atendimento pode seguir sem pressao financeira imediata.'
                ),
                'count': len(data['queue']),
                'pill_class': 'warning' if first_payment else 'info',
                'href': '#reception-payment-board',
                'href_label': 'Ver cobranca curta',
            },
            {
                **_build_reception_focus_signal(count=len(data['sessions']), active_class='severity-cyan'),
                'label': 'Feche orientando a proxima aula',
                'chip_label': 'Aulas',
                'summary': (
                    f'{next_session.title} e a proxima aula visivel para responder horario, coach e duvida rapida sem abrir gestao de agenda.'
                    if next_session else
                    'Sem aula futura no recorte atual, entao a leitura da grade nao e o ponto de pressao desta rodada.'
                ),
                'count': len(data['sessions']),
                'pill_class': 'accent',
                'href': '#reception-class-grid-board',
                'href_label': 'Ver grade em leitura',
            },
        ],
        'reception_decision_entry_context': reception_decision_entry_context,
        'reception_boundaries': [
            'A Recepcao acolhe, localiza, cadastra e encaminha sem assumir o papel do manager.',
            'A grade aqui continua em leitura apenas: orientar o balcao nao significa gerenciar agenda.',
            'A cobranca curta resolve pagamento e ajuste simples sem abrir o centro financeiro completo.',
        ],
        'reception_payment_methods': data['payment_methods'],
        'reception_queue': data['queue'],
        'reception_intakes': data['intakes'],
        'reception_sessions': data['sessions'],
    }


__all__ = [
    'build_coach_workspace_snapshot',
    'build_dev_workspace_snapshot',
    'build_manager_workspace_snapshot',
    'build_owner_workspace_snapshot',
    'build_reception_workspace_snapshot',
]

