"""
ARQUIVO: corredor de leitura do workspace de manager.

POR QUE ELE EXISTE:
- tira de `operations/queries.py` o bloco mais denso e mais propenso a crescer.

O QUE ESTE ARQUIVO FAZ:
1. monta a leitura operacional do manager.
2. aplica decisoes de intake, vinculo e cobranca.
3. fecha o payload de transporte do manager sem depender da borda HTTP.

PONTOS CRITICOS:
- manter semantica, payload e queries estaveis durante a extracao.
- este corredor ainda compartilha alguns utilitarios com `operations/queries.py` de forma indireta.
"""

from datetime import timedelta
from urllib.parse import quote

from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_OWNER, ROLE_RECEPTION
from auditing.models import AuditEvent
from communications.application.message_templates import build_operational_message_body
from communications.queries import get_unlinked_whatsapp_contacts
from finance.models import Payment, PaymentStatus
from monitoring.beacon_snapshot import build_red_beacon_snapshot
from onboarding.models import IntakeStatus
from onboarding.queries import get_pending_intakes
from shared_support.operational_contact_memory import (
    ACTION_LABELS,
    CONTACT_COOLDOWN_DAYS,
    CONTACT_HISTORY_LOOKBACK_DAYS,
    CONTACT_MEMORY_ACTIONS,
    FINANCE_CONTACT_ACTIONS,
    ROLE_LABELS,
    SURFACE_LABELS,
    TEAM_CONTACT_ROLE_SLUGS,
    build_contact_subject_key,
    is_finance_contact_action,
    is_intake_contact_action,
)
from shared_support.phone_numbers import normalize_phone_number
from shared_support.workspace_snapshot_versions import build_workspace_snapshot_version


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


def _with_fragment(url, fragment):
    return f'{url}{fragment}' if fragment else url


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


def _serialize_manager_intake(intake):
    return {
        'id': intake.id,
        'full_name': intake.full_name,
        'phone': intake.phone,
        'email': getattr(intake, 'email', ''),
        'source': getattr(intake, 'source', ''),
        'source_label': intake.get_source_display(),
        'status': getattr(intake, 'status', ''),
        'status_label': intake.get_status_display(),
        'contact_subject_key': getattr(intake, 'contact_subject_key', ''),
        'decision_action': getattr(intake, 'decision_action', {}),
    }


def _serialize_manager_contact(contact):
    return {
        'id': contact.id,
        'display_name': getattr(contact, 'display_name', ''),
        'phone': getattr(contact, 'phone', ''),
        'status': getattr(contact, 'status', ''),
        'status_label': contact.get_status_display(),
        'contact_subject_key': getattr(contact, 'contact_subject_key', ''),
        'decision_action': getattr(contact, 'decision_action', {}),
    }


def _serialize_manager_payment(payment):
    return {
        'id': payment.id,
        'student_id': payment.student.id,
        'student_full_name': payment.student.full_name,
        'student_event_stream_url': reverse('student-event-stream', args=[payment.student.id]),
        'contact_subject_key': getattr(payment, 'contact_subject_key', ''),
        'due_date': payment.due_date,
        'due_date_label': payment.due_date.strftime('%d/%m/%Y') if payment.due_date else '',
        'status': payment.status,
        'status_label': payment.get_status_display(),
        'status_class': 'warning' if payment.status in [PaymentStatus.OVERDUE, PaymentStatus.PENDING] else 'info',
        'amount': payment.amount,
        'amount_label': f'R$ {payment.amount:.2f}',
        'decision_action': getattr(payment, 'decision_action', {}),
        'team_touch_label': getattr(payment, 'team_touch_label', ''),
        'team_touch_note': getattr(payment, 'team_touch_note', ''),
        'whatsapp_action': getattr(payment, 'whatsapp_action', None),
    }


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
                f'{pending_intakes_count} contato(s) já chegaram e pedem triagem agora para não virarem fila morta.'
                if has_intakes else
                'Nenhuma entrada pede triagem agora; a fila comercial está limpa.'
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
            label='Vínculos quebrados' if has_links else 'Vínculos estáveis',
            chip_label='Vínculos',
            summary=(
                f'{unlinked_whatsapp_count} contato(s) e {payments_without_enrollment_count} cobrança(s) ainda estão soltos e escondem atrito estrutural na operação.'
                if has_links else
                'Sem contato ou cobrança solta agora; a estrutura está consistente.'
            ),
            count=links_count,
            pill_class='info' if has_links else 'success',
            href='#manager-link-board',
            href_label='Corrigir vínculos' if has_links else 'Checar vínculos',
            status_mode='watch' if has_links else 'clean',
            priority_score=priority_order['links'] + links_count,
        ),
        _build_manager_focus_item(
            key='finance',
            label='Receita em risco' if has_finance else 'Caixa estável',
            chip_label='Cobrança',
            summary=(
                f'{financial_alerts_count} alerta(s) já pedem ação para evitar atraso, evasão ou ruído no caixa.'
                if has_finance else
                'Nenhum alerta financeiro pressiona o caixa agora; a leitura está estável.'
            ),
            count=financial_alerts_count,
            pill_class='warning' if has_finance else 'success',
            href='#manager-finance-board',
            href_label='Atacar cobranças' if has_finance else 'Revisar caixa',
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
            'title': 'Comece pela triagem para não perder entrada quente.',
            'copy': 'A fila comercial tem demanda esperando resposta e deve abrir a leitura do manager.',
            'pill_label': 'Entradas',
            'pill_class': 'warning',
        }
    if primary_key == 'finance' and status_mode == 'act_now':
        return {
            'title': 'Comece pela cobrança antes que isso vire ruído no caixa.',
            'copy': 'Sem triagem pressionando mais forte, os alertas financeiros viram a camada dominante do turno.',
            'pill_label': 'Cobrança',
            'pill_class': 'warning',
        }
    if primary_key == 'links' and status_mode in ['watch', 'act_now']:
        return {
            'title': 'Corrija vínculos antes de empilhar exceções.',
            'copy': 'Contato sem aluno e cobrança sem matrícula escondem atrito estrutural que contamina o resto da operação.',
            'pill_label': 'Vínculos',
            'pill_class': 'info',
        }
    return {
        'title': 'A mesa está limpa para leitura de manutenção.',
        'copy': 'Sem pressão dominante, a gerência pode validar a operação com mais calma e menos reatividade.',
        'pill_label': 'Estável',
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
                'title': 'Quem pede triagem agora' if has_intakes else 'Fila de entradas sob controle',
                'copy': (
                    'A primeira resposta destrava a fila e evita lead esfriando.'
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
                'title': 'Nenhuma entrada pede triagem agora',
                'copy': 'A triagem inicial não tem novo contato aguardando encaminhamento neste momento.',
                'badge': 'Base limpa',
                'badge_class': 'accent',
            },
        },
        'links': {
            'key': 'links',
            'status_mode': 'watch' if has_links else 'clean',
            'header': {
                'eyebrow': 'Vínculos',
                'title': 'Contatos ainda sem aluno' if has_links else 'Vínculos de contato estáveis',
                'copy': (
                    'Conversa solta vira atrito estrutural se ninguem conectar agora.'
                    if has_links else
                    'Nenhuma conversa pede conexao com aluno neste momento.'
                ),
                'pill_label': f'{unlinked_whatsapp_count} contato(s)' if has_links else 'Inbox organizado',
                'pill_class': 'info' if has_links else 'accent',
            },
            'empty': {
                'eyebrow': 'Vínculos',
                'title': 'Nenhum contato pendente',
                'copy': 'Não há conversa solta exigindo identificação ou conexão com aluno agora.',
                'badge': 'Inbox organizado',
                'badge_class': 'info',
            },
        },
        'enrollment_links': {
            'key': 'enrollment_links',
            'status_mode': 'watch' if has_enrollment_gaps else 'clean',
            'header': {
                'eyebrow': 'Vínculos',
                'title': 'Cobranças ainda sem matrícula' if has_enrollment_gaps else 'Estrutura financeira coerente',
                'copy': (
                    'Resolva os vencimentos mais proximos antes que o financeiro herde estrutura quebrada.'
                    if has_enrollment_gaps else
                    'Sem cobrança solta sem matrícula, a base financeira segue coerente.'
                ),
                'pill_label': f'{payments_without_enrollment_count} pendencia(s)' if has_enrollment_gaps else 'Estrutura coerente',
                'pill_class': 'info' if has_enrollment_gaps else 'accent',
                'live_pill_label': 'Escuta pronta',
                'live_pill_class': 'neutral',
            },
            'empty': {
                'eyebrow': 'Vínculos',
                'title': 'Nenhum pagamento aguardando vinculo',
                'copy': 'A estrutura financeira não tem cobrança solta sem matrícula ativa neste recorte.',
                'badge': 'Estrutura coerente',
                'badge_class': 'accent',
            },
        },
        'finance': {
            'key': 'finance',
            'status_mode': 'act_now' if has_finance else 'clean',
            'header': {
                'eyebrow': 'Cobrança',
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
                'title': 'Historico da gerencia',
                'copy': (
                    'Veja as ultimas abordagens para nao repetir a mesma porta antes de trocar a estrategia.'
                    if history_count else
                    'As ultimas abordagens da gerencia aparecerao aqui conforme os contatos forem acontecendo.'
                ),
                'pill_label': f'{history_count} acao(oes)' if history_count else '15 dias',
                'pill_class': 'info' if history_count else 'accent',
            },
            'empty': {
                'eyebrow': 'Historico',
                'title': 'Nenhuma abordagem recente',
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


def build_manager_workspace_snapshot(*, actor=None):
    today = timezone.localdate()
    red_beacon_snapshot = build_red_beacon_snapshot()
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

    payments_without_enrollment = list(
        Payment.objects.select_related('student').filter(
            enrollment__isnull=True,
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        ).order_by('due_date')[:8]
    )
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
    transport_payload = {
        'pending_intakes': [_serialize_manager_intake(intake) for intake in pending_intakes],
        'unlinked_whatsapp': [_serialize_manager_contact(contact) for contact in unlinked_whatsapp],
        'financial_alerts': [_serialize_manager_payment(payment) for payment in financial_alerts],
        'payments_without_enrollment': [_serialize_manager_payment(payment) for payment in payments_without_enrollment],
        'manager_recent_history': manager_recent_history,
    }
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
            {
                **_build_metric_card('operation-kpi-card manager-beacon', 'Red Beacon', red_beacon_snapshot['signal_mesh']['total_due_backlog']),
                'note': red_beacon_snapshot['summary'],
                'status_hint': 'attention' if red_beacon_snapshot['signal_mesh']['total_due_backlog'] > 0 else 'clean',
                'href': '#manager-history-board',
            },
        ],
        'manager_operational_focus': manager_operational_focus,
        'red_beacon_snapshot': red_beacon_snapshot,
        'transport_payload': transport_payload,
    }
