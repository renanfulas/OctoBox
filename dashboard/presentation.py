"""
ARQUIVO: presentation do dashboard principal.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem estrutural do painel principal.
- mantem a borda HTTP curta e o contrato da tela explicito.
"""

from django.utils import timezone

from access.navigation_contracts import get_shell_route_url
from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from django.urls import reverse
from shared_support.page_payloads import (
    build_page_assets,
    build_page_hero,
    build_page_payload,
    build_page_reading_panel,
    select_priority_items,
)


READING_CARD_SEVERITY_ORDER = ('emergency', 'warning', 'risk')


def _get_student_name(student):
    if isinstance(student, dict):
        return student.get('full_name') or 'Alguem'
    return getattr(student, 'full_name', 'Alguem')


def _get_student_absences(student):
    if isinstance(student, dict):
        return student.get('total_absences', 0) or 0
    return getattr(student, 'total_absences', 0) or 0


def _get_payment_alert_student_name(payment_alert):
    if not payment_alert:
        return 'Alguem'
    if isinstance(payment_alert, dict):
        return payment_alert.get('student_full_name') or 'Alguem'
    student = getattr(payment_alert, 'student', None)
    return getattr(student, 'full_name', 'Alguem')




def _build_dashboard_hero_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return [
            {'label': 'Abrir balcao', 'href': get_shell_route_url('reception'), 'kind': 'primary'},
            {'label': 'Novo aluno', 'href': reverse('student-quick-create'), 'kind': 'secondary'},
        ]

    return [
        {'label': 'Abrir alunos', 'href': get_shell_route_url('students'), 'kind': 'primary'},
        {'label': 'Abrir financeiro', 'href': get_shell_route_url('finance', fragment='finance-priority-board'), 'kind': 'secondary'},
    ]


def _build_dashboard_hero_copy(role_slug):
    if role_slug == ROLE_RECEPTION:
        return 'Veja o balcao, a base e o caixa curto sem perder o ritmo.'

    return 'Veja a frente dominante e desca para agir sem ruido.'


def _build_dashboard_quick_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return [
            {
                'eyebrow': 'Chegada',
                'title': 'Novo aluno',
                'copy': 'Alguem chegou. Vou te guiar pra ficha ficar pronta rapido.',
                'href': reverse('student-quick-create'),
            },
            {
                'eyebrow': 'Caixa',
                'title': 'Cobrancas do dia',
                'copy': 'Separei o que precisa sair agora. Pode confiar, esta tudo aqui.',
                'href': get_shell_route_url('reception', fragment='reception-payment-board'),
            },
            {
                'eyebrow': 'Agenda viva',
                'title': 'Grade do turno',
                'copy': 'Organizei horario, coach e vagas pra voce responder com seguranca.',
                'href': get_shell_route_url('classes'),
            },
        ]
    
    if role_slug == ROLE_COACH:
        return [
            {
                'eyebrow': 'Fila principal',
                'title': 'Rota de entradas',
                'copy': 'Tem gente nova na porta. Vou te mostrar como isso muda o turno.',
                'href': get_shell_route_url('intake'),
            },
            {
                'eyebrow': 'Presenca',
                'title': 'Registrar turma',
                'copy': 'Sua turma esta esperando. Comece por aqui e eu acompanho contigo.',
                'href': get_shell_route_url('coach', fragment='coach-boundary-board'),
            },
            {
                'eyebrow': 'Agenda viva',
                'title': 'Turmas em movimento',
                'copy': 'Montei a composicao das turmas pra voce. So confirmar e seguir.',
                'href': get_shell_route_url('classes'),
            },
        ]

    return [
        {
            'eyebrow': 'Quem chega',
            'title': 'Novas entradas',
            'copy': 'Tem gente chegando. Vou te mostrar onde ainda da pra criar vinculo.',
            'href': get_shell_route_url('intake'),
        },
        {
            'eyebrow': 'Agenda',
            'title': 'As turmas do dia',
            'copy': 'A agenda esta aqui. Eu cuido da leitura, voce decide o passo.',
            'href': get_shell_route_url('classes'),
        },
        {
            'eyebrow': 'Caixa',
            'title': 'Receita e saude',
            'copy': 'Separei o que entrou e o que ainda pede cuidado. Voce vai saber o que fazer.',
            'href': get_shell_route_url('finance', fragment='finance-priority-board'),
        },
    ]


def _can_register_finance_whatsapp(role_slug):
    return role_slug in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION}


def _build_dashboard_layout(role_slug):
    del role_slug

    slot_contract = [
        {
            'id': 'hero',
            'label': 'Abertura',
            'description': 'Recebe o manifesto operacional do dia e as acoes principais.',
            'allows_reorder': False,
        },
        {
            'id': 'main_primary',
            'label': 'Leitura principal',
            'description': 'Agrupa o painel central do dashboard com resumo rapido e metricas.',
            'allows_reorder': True,
        },
        {
            'id': 'right_rail',
            'label': 'Trilho de apoio',
            'description': 'Sustenta a decisao principal com agenda e leitura lateral.',
            'allows_reorder': True,
        },
    ]

    block_registry = [
        {
            'id': 'hero',
            'label': 'Hero',
            'slot': 'hero',
            'allowed_slots': ['hero'],
            'default_order': 10,
            'template': 'dashboard/blocks/hero.html',
            'movable': False,
            'collapsible': False,
            'removable': False,
        },
        {
            'id': 'metrics_cluster',
            'label': 'Metricas',
            'slot': 'main_primary',
            'allowed_slots': ['main_primary', 'right_rail'],
            'default_order': 10,
            'template': 'dashboard/blocks/metrics_cluster.html',
            'movable': True,
            'collapsible': False,
            'removable': True,
        },
        {
            'id': 'sessions_board',
            'label': 'Agenda',
            'slot': 'right_rail',
            'allowed_slots': ['right_rail', 'main_primary'],
            'default_order': 20,
            'template': 'dashboard/blocks/sessions_board.html',
            'movable': True,
            'collapsible': True,
            'removable': False,
        },
    ]

    layout_state = _normalize_dashboard_layout_state(
        None,
        slot_contract=slot_contract,
        block_registry=block_registry,
    )
    slots = _build_dashboard_slots(
        slot_contract=slot_contract,
        block_registry=block_registry,
        layout_state=layout_state,
    )
    hidden_blocks = _build_dashboard_hidden_blocks(
        block_registry=block_registry,
        layout_state=layout_state,
    )

    return {
        'version': 'v2',
        'slot_contract': slot_contract,
        'block_registry': block_registry,
        'layout_state': layout_state,
        'slots': slots,
        'hidden_blocks': hidden_blocks,
    }


def _build_dashboard_default_layout_state(*, slot_contract, block_registry):
    default_state = {slot['id']: [] for slot in slot_contract}
    for block in sorted(block_registry, key=lambda item: item['default_order']):
        default_state[block['slot']].append(block['id'])
    return default_state


def _normalize_dashboard_layout_state(layout_state, *, slot_contract, block_registry):
    slot_ids = [slot['id'] for slot in slot_contract]
    block_by_id = {block['id']: block for block in block_registry}
    collapsible_block_ids = {
        block['id']
        for block in block_registry
        if block.get('collapsible')
    }
    removable_block_ids = {
        block['id']
        for block in block_registry
        if block.get('removable')
    }
    normalized_slots = {slot_id: [] for slot_id in slot_ids}
    raw_slots = layout_state.get('slots') if isinstance(layout_state, dict) else None
    raw_collapsed_blocks = layout_state.get('collapsed_blocks') if isinstance(layout_state, dict) else None
    raw_hidden_blocks = layout_state.get('hidden_blocks') if isinstance(layout_state, dict) else None
    normalized_hidden_blocks = []
    seen = set()

    if isinstance(raw_hidden_blocks, list):
        for block_id in raw_hidden_blocks:
            if block_id not in removable_block_ids:
                continue
            if block_id in normalized_hidden_blocks:
                continue
            normalized_hidden_blocks.append(block_id)

    if isinstance(raw_slots, dict):
        for slot_id in slot_ids:
            candidate_ids = raw_slots.get(slot_id)
            if not isinstance(candidate_ids, list):
                continue
            for block_id in candidate_ids:
                if block_id in seen or block_id not in block_by_id:
                    continue
                if block_id in normalized_hidden_blocks:
                    continue
                if slot_id not in block_by_id[block_id]['allowed_slots']:
                    continue
                normalized_slots[slot_id].append(block_id)
                seen.add(block_id)

    default_state = _build_dashboard_default_layout_state(slot_contract=slot_contract, block_registry=block_registry)
    for slot_id in slot_ids:
        for block_id in default_state[slot_id]:
            if block_id in seen:
                continue
            if block_id in normalized_hidden_blocks:
                continue
            normalized_slots[slot_id].append(block_id)
            seen.add(block_id)

    normalized_collapsed_blocks = []
    if isinstance(raw_collapsed_blocks, list):
        for block_id in raw_collapsed_blocks:
            if block_id not in collapsible_block_ids:
                continue
            if block_id not in seen:
                continue
            if block_id in normalized_collapsed_blocks:
                continue
            normalized_collapsed_blocks.append(block_id)

    return {
        'slots': normalized_slots,
        'collapsed_blocks': normalized_collapsed_blocks,
        'hidden_blocks': normalized_hidden_blocks,
    }


def _decorate_dashboard_block(block, *, slot_id, layout_state, is_hidden=False):
    decorated = dict(block)
    decorated['default_slot'] = block['slot']
    decorated['slot'] = slot_id
    decorated['is_collapsed'] = decorated['id'] in layout_state.get('collapsed_blocks', [])
    decorated['is_hidden'] = is_hidden
    return decorated


def _build_dashboard_slots(*, slot_contract, block_registry, layout_state):
    block_by_id = {block['id']: block for block in block_registry}
    slots = {slot['id']: [] for slot in slot_contract}
    for slot in slot_contract:
        for block_id in layout_state['slots'][slot['id']]:
            slots[slot['id']].append(
                _decorate_dashboard_block(
                    block_by_id[block_id],
                    slot_id=slot['id'],
                    layout_state=layout_state,
                )
            )
    return slots


def _build_dashboard_hidden_blocks(*, block_registry, layout_state):
    block_by_id = {block['id']: block for block in block_registry}
    hidden_blocks = []
    for block_id in layout_state.get('hidden_blocks', []):
        hidden_blocks.append(
            _decorate_dashboard_block(
                block_by_id[block_id],
                slot_id=block_by_id[block_id]['slot'],
                layout_state=layout_state,
                is_hidden=True,
            )
        )
    return hidden_blocks


def build_dashboard_layout(role_slug, *, stored_layout_state=None):
    layout = _build_dashboard_layout(role_slug)
    layout_state = _normalize_dashboard_layout_state(
        stored_layout_state,
        slot_contract=layout['slot_contract'],
        block_registry=layout['block_registry'],
    )
    layout['layout_state'] = layout_state
    layout['slots'] = _build_dashboard_slots(
        slot_contract=layout['slot_contract'],
        block_registry=layout['block_registry'],
        layout_state=layout_state,
    )
    layout['hidden_blocks'] = _build_dashboard_hidden_blocks(
        block_registry=layout['block_registry'],
        layout_state=layout_state,
    )
    return layout


def _build_dashboard_execution_focus(role_slug, *, next_session, next_payment_alert, highest_risk_student, actionable_payment_alerts_count):
    finance_label = 'Cuido do caixa contigo. Comece por aqui'
    finance_summary = (
        f'{actionable_payment_alerts_count} cobranca(s) pedem contato. {_get_payment_alert_student_name(next_payment_alert)} e o melhor ponto pra comecar. Voce consegue resolver isso.'
        if next_payment_alert else
        'Nenhuma cobranca critica agora. O caixa esta bem e voce pode respirar.'
    )
    finance_href = get_shell_route_url('finance', fragment='finance-priority-board')
    finance_href_label = 'Abrir financeiro'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Essa cobranca cabe no seu turno. Vamos juntos'
        finance_summary = (
            f'{actionable_payment_alerts_count} cobranca(s) pedem sua atencao. {_get_payment_alert_student_name(next_payment_alert)} e quem mais precisa de voce agora.'
            if next_payment_alert else
            'O caixa curto esta tranquilo. Voce esta dando conta.'
        )
        finance_href = get_shell_route_url('reception', fragment='reception-payment-board')
        finance_href_label = 'Abrir cobrancas do balcao'

    return [
        {
            'label': finance_label,
            'chip_label': 'Caixa' if role_slug == ROLE_RECEPTION else 'Cobrancas',
            'count': actionable_payment_alerts_count,
            'summary': finance_summary,
            'pill_class': 'warning' if next_payment_alert else 'success',
            'href': finance_href,
            'href_label': finance_href_label,
        },
        {
            'label': 'A agenda esta pronta pra voce conferir',
            'chip_label': 'Aulas',
            'summary': (
                f"{next_session['title']} e a proxima. Deixei tudo organizado pra voce so confirmar."
                if next_session else
                'Sem aulas no radar agora. Aproveita esse respiro, voce merece.'
            ),
            'pill_class': 'info' if next_session else 'accent',
            'href': '#dashboard-sessions-board',
            'href_label': 'Abrir agenda do dia',
        },
        {
            'label': 'Tem alguem que precisa de voce' if role_slug != ROLE_RECEPTION else 'Feche com quem pede acolhimento',
            'chip_label': 'Risco' if role_slug != ROLE_RECEPTION else 'Retencao',
            'summary': (
                f'{_get_student_name(highest_risk_student)} sumiu um pouco com {_get_student_absences(highest_risk_student)} falta(s). Um contato seu pode trazer de volta. Voce consegue.'
                if highest_risk_student else
                ('A base esta firme. Ninguem mostra sinal de esfriamento. Voce esta cuidando bem.' if role_slug != ROLE_RECEPTION else 'Ninguem precisa de resgate agora. O balcao esta acolhendo bem.')
            ),
            'pill_class': 'warning' if highest_risk_student else 'success',
            'href': get_shell_route_url('students'),
            'href_label': 'Abrir alunos em atencao' if role_slug != ROLE_RECEPTION else 'Abrir alunos que pedem cuidado',
        },
    ]


def _build_dashboard_priority_cards(
    role_slug,
    *,
    metrics,
    upcoming_sessions,
    next_session,
    payment_alerts,
    next_payment_alert,
    actionable_payment_alerts_count,
    highest_risk_student,
):
    finance_href = get_shell_route_url('reception', fragment='reception-payment-board') if role_slug == ROLE_RECEPTION else get_shell_route_url('finance', fragment='finance-priority-board')
    primary_payment_alert = next_payment_alert or (payment_alerts[0] if payment_alerts else None)
    overdue_count = metrics['overdue_payments']

    def build_priority_card(*, severity, value, surface, href_label='Abrir prioridade', **card):
        return {
            **card,
            'severity': severity,
            'surface': surface,
            'is_actionable': value > 0,
            'href_label': href_label,
            'value': value,
        }

    student_name = 'Alguem'
    if primary_payment_alert:
        student_name = _get_payment_alert_student_name(primary_payment_alert)

    if actionable_payment_alerts_count > 0 and primary_payment_alert:
        emergency_card = build_priority_card(
            severity='emergency',
            value=actionable_payment_alerts_count,
            surface='finance',
            href=finance_href,
            href_label='Abrir financeiro',
            card_class='is-finance',
            indicator_class='is-finance',
            kicker='Emergencia',
            indicator='Caixa' if role_slug == ROLE_RECEPTION else 'Urgente',
            copy=(
                f'{student_name} esta esperando contato. Eu te guio: comece por aqui e o caixa agradece.'
                if role_slug != ROLE_RECEPTION else
                f'{student_name} precisa do seu cuidado agora. Uma abordagem sua faz toda a diferenca.'
            ),
        )
    elif overdue_count > 0 and primary_payment_alert:
        emergency_card = build_priority_card(
            severity='emergency',
            value=overdue_count,
            surface='finance',
            href=finance_href,
            href_label='Abrir financeiro',
            card_class='is-finance',
            indicator_class='is-finance',
            kicker='Emergencia',
            indicator='Controle',
            copy=(
                f'{student_name} abre a fila. O dinheiro ainda esta ai, so precisa de voce. Vamos resolver juntos.'
                if role_slug != ROLE_RECEPTION else
                f'{student_name} abre a fila curta. O caixa respira, mas uma olhada sua agora faz diferenca.'
            ),
        )
    else:
        emergency_card = build_priority_card(
            severity='emergency',
            value=0,
            surface='finance',
            href=finance_href,
            href_label='Abrir financeiro',
            card_class='is-finance',
            indicator_class='is-finance',
            kicker='Emergencia',
            indicator='Estavel',
            copy=(
                'Caixa limpo. Voce esta no controle. Pode seguir com tranquilidade.'
                if role_slug != ROLE_RECEPTION else
                'Tudo certo no caixa do balcao. Voce esta mandando bem.'
            ),
        )

    pressured_session = next(
        (
            session for session in upcoming_sessions
            # Uma aula vira prioridade quando o turno esta sob pressao real:
            # lotacao alta, reservas fechadas ou runtime ao vivo pedindo coordenacao.
            if (
                session.get('status_label') == 'Em andamento'
                or session.get('occupancy_percent', 0) >= 90
                or session.get('booking_closed')
            )
        ),
        None,
    )

    if pressured_session:
        starts_at = pressured_session.get('starts_at')
        starts_at_label = timezone.localtime(starts_at).strftime('%H:%M') if starts_at else '--:--'
        urgency_card = build_priority_card(
            severity='warning',
            value=pressured_session['occupancy_percent'] or len(upcoming_sessions),
            surface='sessions',
            href='#dashboard-sessions-board',
            href_label='Abrir agenda do dia',
            card_class='is-sessions',
            indicator_class='is-sessions',
            kicker='Urgente',
            indicator='Turno',
            copy=(
                f"{pressured_session['title']} esta acontecendo agora. Eu cuido da leitura, voce cuida da equipe."
                if pressured_session['status_label'] == 'Em andamento' else
                f"{pressured_session['title']} comeca as {starts_at_label} e precisa de atencao. Vou te levar pra agenda."
            ),
        )
    elif highest_risk_student and _get_student_absences(highest_risk_student) >= 1:
        urgency_card = build_priority_card(
            severity='warning',
            value=_get_student_absences(highest_risk_student),
            surface='students',
            href=get_shell_route_url('students'),
            href_label='Abrir alunos em atencao',
            card_class='is-base',
            indicator_class='is-base',
            kicker='Urgente',
            indicator='Retencao' if role_slug != ROLE_RECEPTION else 'Cuidado',
            copy=(
                f'{_get_student_name(highest_risk_student)} sumiu um pouco, {_get_student_absences(highest_risk_student)} falta(s). Uma mensagem sua pode ser o que faltava pra voltar.'
                if role_slug != ROLE_RECEPTION else
                f'{_get_student_name(highest_risk_student)} precisa sentir que alguem notou, {_get_student_absences(highest_risk_student)} falta(s). Seu acolhimento pode mudar tudo.'
            ),
        )
    else:
        urgency_card = build_priority_card(
            severity='warning',
            value=0,
            surface='students',
            href=get_shell_route_url('students'),
            href_label='Abrir alunos',
            card_class='is-base',
            indicator_class='is-base',
            kicker='Urgente',
            indicator='Estavel',
            copy='Tudo tranquilo na reten. A comunidade esta bem e voce pode focar no que quiser.',
        )

    occurrences_count = metrics['occurrences_this_month']
    if occurrences_count > 0 and highest_risk_student:
        risk_card = build_priority_card(
            severity='risk',
            value=occurrences_count,
            surface='students',
            href=get_shell_route_url('students'),
            href_label='Abrir alunos',
            card_class='is-risk',
            indicator_class='is-risk',
            kicker='Risco',
            indicator='Rotina',
            copy=(
                f'{occurrences_count} ocorrencia(s) no mes e {_get_student_name(highest_risk_student)} com {_get_student_absences(highest_risk_student)} falta(s). Eu organizo os dados, voce decide a acao. Juntos resolvemos.'
                if role_slug != ROLE_RECEPTION else
                f'{occurrences_count} ocorrencia(s) no mes e {_get_student_name(highest_risk_student)} pede acolhimento. Eu te mostro por onde comecar.'
            ),
        )
    elif occurrences_count > 0:
        risk_card = build_priority_card(
            severity='risk',
            value=occurrences_count,
            surface='students',
            href=get_shell_route_url('students'),
            href_label='Abrir alunos',
            card_class='is-risk',
            indicator_class='is-risk',
            kicker='Risco',
            indicator='Rotina',
            copy='Algumas ocorrencias apareceram. Vou te ajudar a organizar antes que vire problema.',
        )
    else:
        risk_card = build_priority_card(
            severity='risk',
            value=0,
            surface='students',
            href=get_shell_route_url('students'),
            href_label='Abrir alunos',
            card_class='is-risk',
            indicator_class='is-risk',
            kicker='Risco',
            indicator='Estavel',
            copy='Rotina limpa. O box esta funcionando bem e voce pode confiar no ritmo.',
        )

    return [emergency_card, urgency_card, risk_card]


def _select_dashboard_reading_cards(priority_cards):
    """Mantem a faixa de leitura completa na ordem operacional: emergency > warning > risk."""
    ordered_cards = []
    for priority in READING_CARD_SEVERITY_ORDER:
        selected_item = next((item for item in list(priority_cards or []) if item.get('severity') == priority), None)
        if selected_item:
            ordered_cards.append(selected_item)
    return ordered_cards


def _build_dashboard_reading_panel(priority_cards, *, role_slug=''):
    selected_cards = _select_dashboard_reading_cards(priority_cards)
    items = []
    for card in selected_cards:
        is_tranquil = not card.get('is_actionable')
        if role_slug == ROLE_MANAGER and is_tranquil and (card.get('value') or 0) == 0:
            continue
        items.append(
            {
                'chip_label': card.get('indicator') or card.get('kicker'),
                'count': card.get('value'),
                'label': card.get('kicker') or 'Leitura dominante',
                'summary': card.get('copy', ''),
                'pill_class': 'success' if is_tranquil else ('warning' if card.get('severity') in ('emergency', 'warning') else 'accent'),
                'severity_class': '' if is_tranquil else (f"is-{card.get('severity')}" if card.get('severity') else ''),
                'is_tranquil': is_tranquil,
                'is_clickable': not is_tranquil,
                'href': card.get('href', '#dashboard'),
                'href_label': card.get('href_label', 'Abrir leitura'),
            }
        )

    primary_card = selected_cards[0] if selected_cards else {}
    return build_page_reading_panel(
        items=items,
        primary_href=primary_card.get('href', ''),
        class_name='dashboard-reading-panel',
        panel_id='dashboard-reading-panel',
    )


def build_dashboard_page(*, request_user, role_slug, snapshot, stored_layout_state=None):
    upcoming_sessions = list(snapshot['upcoming_sessions'])
    student_health = list(snapshot['student_health'])
    payment_alerts = list(snapshot['payment_alerts'])
    next_session = upcoming_sessions[0] if upcoming_sessions else None
    actionable_payment_alerts_count = snapshot.get('actionable_payment_alerts_count', 0)
    next_payment_alert = snapshot.get('next_actionable_payment_alert')
    highest_risk_student = next((student for student in student_health if _get_student_absences(student) >= 1), None)
    execution_focus = _build_dashboard_execution_focus(
        role_slug,
        next_session=next_session,
        next_payment_alert=next_payment_alert,
        highest_risk_student=highest_risk_student,
        actionable_payment_alerts_count=actionable_payment_alerts_count,
    )
    priority_cards = _build_dashboard_priority_cards(
        role_slug,
        metrics=snapshot['metrics'],
        upcoming_sessions=upcoming_sessions,
        next_session=next_session,
        payment_alerts=payment_alerts,
        next_payment_alert=next_payment_alert,
        actionable_payment_alerts_count=actionable_payment_alerts_count,
        highest_risk_student=highest_risk_student,
    )
    pending_focus = {
        'href': get_shell_route_url('reception', fragment='reception-intake-board') if role_slug == ROLE_RECEPTION else get_shell_route_url('intake', fragment='intake-queue-board'),
        'summary': 'Tem gente esperando um retorno seu. Vou te levar ate la.',
    }
    hero = build_page_hero(
        eyebrow='Hoje',
        title='Dia em leitura.',
        copy=_build_dashboard_hero_copy(role_slug),
        actions=_build_dashboard_hero_actions(role_slug),
        aria_label='Panorama do dia',
        classes=['dashboard-command-hero'],
        data_slot='hero',
        data_panel='dashboard-hero',
    )
    dashboard_layout = build_dashboard_layout(role_slug, stored_layout_state=stored_layout_state)

    return build_page_payload(
        context={
            'page_key': 'dashboard',
            'title': 'Dashboard do box',
            'subtitle': 'Tudo o que voce precisa, no tempo certo.',
            'mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
            'role_slug': role_slug,
        },
        data={
            **snapshot,
            'hero': hero,
            'reading_panel': _build_dashboard_reading_panel(priority_cards, role_slug=role_slug),
            'dashboard_layout': dashboard_layout,
            'dashboard_role_mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
            'dashboard_can_register_finance_whatsapp': _can_register_finance_whatsapp(role_slug),
            'dashboard_quick_actions': _build_dashboard_quick_actions(role_slug),
            'dashboard_execution_focus': execution_focus,
            'dashboard_priority_cards': priority_cards,
        },
        behavior={
            'dashboard_layout_save_url': '/dashboard/layout/',
            'dashboard_layout_version': dashboard_layout['version'],
        },
        assets=build_page_assets(
            css=[
                'css/design-system/operations.css',
                'css/design-system/dashboard.css',
                'css/design-system/components/dashboard/layout.css',
            ],
            js=[
                'js/pages/dashboard/dashboard-layout-controller.js',
                'js/pages/dashboard/dashboard.js',
            ],
        ),
    )

