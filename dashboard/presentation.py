"""
ARQUIVO: presentation do dashboard principal.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem estrutural do painel principal.
- mantem a borda HTTP curta e o contrato da tela explicito.
"""

from django.utils import timezone

from access.navigation_contracts import get_shell_route_url
from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from django.urls import reverse
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload




def _build_dashboard_hero_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return [
            {'label': 'Abrir balcao da recepcao', 'href': get_shell_route_url('reception'), 'kind': 'primary'},
            {'label': 'Novo aluno', 'href': reverse('student-quick-create'), 'kind': 'secondary'},
        ]

    return [
        {'label': 'Abrir alunos', 'href': get_shell_route_url('students'), 'kind': 'primary'},
        {'label': 'Abrir financeiro', 'href': get_shell_route_url('finance', fragment='finance-priority-board'), 'kind': 'secondary'},
    ]


def _build_dashboard_hero_copy(role_slug):
    if role_slug == ROLE_RECEPTION:
        return 'Estou aqui com você. Vamos cuidar do balcão juntos.'

    return 'Estou junto contigo. Vamos olhar o que importa hoje.'


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
            'copy': 'Tem gente chegando. Vou te mostrar onde ainda dá pra criar vínculo.',
            'href': get_shell_route_url('intake'),
        },
        {
            'eyebrow': 'Agenda',
            'title': 'As turmas do dia',
            'copy': 'A agenda está aqui. Eu cuido da leitura, você decide o passo.',
            'href': get_shell_route_url('classes'),
        },
        {
            'eyebrow': 'Caixa',
            'title': 'Receita e saúde',
            'copy': 'Separei o que entrou e o que ainda pede cuidado. Você vai saber o que fazer.',
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
            'id': 'priority_strip',
            'label': 'Prioridades',
            'slot': 'main_primary',
            'allowed_slots': ['main_primary', 'right_rail'],
            'default_order': 10,
            'template': 'dashboard/blocks/priority_strip.html',
            'movable': True,
            'collapsible': False,
            'removable': True,
        },
        {
            'id': 'metrics_cluster',
            'label': 'Métricas',
            'slot': 'main_primary',
            'allowed_slots': ['main_primary', 'right_rail'],
            'default_order': 20,
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
            'default_order': 10,
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
        f'{actionable_payment_alerts_count} cobrança(s) pedem contato. {next_payment_alert.student.full_name} é o melhor ponto pra começar. Você consegue resolver isso.'
        if next_payment_alert else
        'Nenhuma cobrança crítica agora. O caixa está bem e você pode respirar.'
    )
    finance_href = get_shell_route_url('finance', fragment='finance-priority-board')
    finance_href_label = 'Abrir financeiro'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Essa cobranca cabe no seu turno. Vamos juntos'
        finance_summary = (
            f'{actionable_payment_alerts_count} cobrança(s) pedem sua atenção. {next_payment_alert.student.full_name} é quem mais precisa de você agora.'
            if next_payment_alert else
            'O caixa curto está tranquilo. Você está dando conta.'
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
                f"{next_session['object'].title} é a próxima. Deixei tudo organizado pra você só confirmar."
                if next_session else
                'Sem aulas no radar agora. Aproveita esse respiro, você merece.'
            ),
            'pill_class': 'info' if next_session else 'accent',
            'href': '#dashboard-sessions-board',
            'href_label': 'Abrir agenda do dia',
        },
        {
            'label': 'Tem alguém que precisa de você' if role_slug != ROLE_RECEPTION else 'Feche com quem pede acolhimento',
            'chip_label': 'Risco' if role_slug != ROLE_RECEPTION else 'Retenção',
            'summary': (
                f'{highest_risk_student.full_name} sumiu um pouco com {highest_risk_student.total_absences} falta(s). Um contato seu pode trazer de volta. Você consegue.'
                if highest_risk_student else
                ('A base está firme. Ninguém mostra sinal de esfriamento. Você está cuidando bem.' if role_slug != ROLE_RECEPTION else 'Ninguém precisa de resgate agora. O balcão está acolhendo bem.')
            ),
            'pill_class': 'warning' if highest_risk_student else 'success',
            'href': get_shell_route_url('students'),
            'href_label': 'Abrir alunos em atenção' if role_slug != ROLE_RECEPTION else 'Abrir alunos que pedem cuidado',
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

    student_name = 'Alguém'
    if primary_payment_alert:
        if isinstance(primary_payment_alert, dict):
            student_name = primary_payment_alert.get('student_full_name') or 'Alguém'
        else:
            student_name = primary_payment_alert.student.full_name if hasattr(primary_payment_alert, 'student') else 'Alguém'

    if actionable_payment_alerts_count > 0 and primary_payment_alert:
        emergency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Emergência',
            'value': actionable_payment_alerts_count,
            'indicator': 'Caixa' if role_slug == ROLE_RECEPTION else 'Urgente',
            'copy': (
                f'{student_name} está esperando contato. Eu te guio: comece por aqui e o caixa agradece.'
                if role_slug != ROLE_RECEPTION else
                f'{student_name} precisa do seu cuidado agora. Uma abordagem sua faz toda a diferença.'
            ),
        }
    elif overdue_count > 0 and primary_payment_alert:
        emergency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Emergência',
            'value': overdue_count,
            'indicator': 'Controle',
            'copy': (
                f'{student_name} abre a fila. O dinheiro ainda está aí, só precisa de você. Vamos resolver juntos.'
                if role_slug != ROLE_RECEPTION else
                f'{student_name} abre a fila curta. O caixa respira, mas uma olhada sua agora faz diferença.'
            ),
        }
    else:
        emergency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Emergência',
            'value': 0,
            'indicator': 'Estável',
            'copy': (
                'Caixa limpo. Você está no controle. Pode seguir com tranquilidade.'
                if role_slug != ROLE_RECEPTION else
                'Tudo certo no caixa do balcão. Você está mandando bem.'
            ),
        }

    pressured_session = next(
        (
            session for session in upcoming_sessions
            if session['status_label'] == 'Em andamento' or session['booking_closed'] or session['occupancy_percent'] >= 90
        ),
        None,
    )

    if highest_risk_student and highest_risk_student.total_absences >= 1:
        urgency_card = {
            'href': get_shell_route_url('students'),
            'card_class': 'is-base',
            'indicator_class': 'is-base',
            'kicker': 'Urgente',
            'value': highest_risk_student.total_absences,
            'indicator': 'Retenção' if role_slug != ROLE_RECEPTION else 'Cuidado',
            'copy': (
                f'{highest_risk_student.full_name} sumiu um pouco, {highest_risk_student.total_absences} falta(s). Uma mensagem sua pode ser o que faltava pra voltar.'
                if role_slug != ROLE_RECEPTION else
                f'{highest_risk_student.full_name} precisa sentir que alguém notou, {highest_risk_student.total_absences} falta(s). Seu acolhimento pode mudar tudo.'
            ),
        }
    elif pressured_session:
        starts_at = pressured_session.get('starts_at')
        starts_at_label = timezone.localtime(starts_at).strftime('%H:%M') if starts_at else '--:--'
        urgency_card = {
            'href': '#dashboard-sessions-board',
            'card_class': 'is-sessions',
            'indicator_class': 'is-sessions',
            'kicker': 'Urgente',
            'value': pressured_session['occupancy_percent'] or len(upcoming_sessions),
            'indicator': 'Turno',
            'copy': (
                f"{pressured_session['object'].title} está acontecendo agora. Eu cuido da leitura, você cuida da equipe."
                if pressured_session['status_label'] == 'Em andamento' else
                f"{pressured_session['object'].title} começa às {starts_at_label} e precisa de atenção. Vou te levar pra agenda."
            ),
        }
    else:
        urgency_card = {
            'href': get_shell_route_url('students'),
            'card_class': 'is-base',
            'indicator_class': 'is-base',
            'kicker': 'Urgente',
            'value': 0,
            'indicator': 'Estável',
            'copy': 'Tudo tranquilo na retenção. A comunidade está bem e você pode focar no que quiser.',
        }

    occurrences_count = metrics['occurrences_this_month']
    if occurrences_count > 0 and highest_risk_student:
        risk_card = {
            'href': get_shell_route_url('students'),
            'card_class': 'is-risk',
            'indicator_class': 'is-risk',
            'kicker': 'Risco',
            'value': occurrences_count,
            'indicator': 'Rotina',
            'copy': (
                f'{occurrences_count} ocorrência(s) no mês e {highest_risk_student.full_name} com {highest_risk_student.total_absences} falta(s). Eu organizo os dados, você decide a ação. Juntos resolvemos.'
                if role_slug != ROLE_RECEPTION else
                f'{occurrences_count} ocorrência(s) no mês e {highest_risk_student.full_name} pede acolhimento. Eu te mostro por onde começar.'
            ),
        }
    elif occurrences_count > 0:
        risk_card = {
            'href': get_shell_route_url('students'),
            'card_class': 'is-risk',
            'indicator_class': 'is-risk',
            'kicker': 'Risco',
            'value': occurrences_count,
            'indicator': 'Rotina',
            'copy': 'Algumas ocorrências apareceram. Vou te ajudar a organizar antes que vire problema.',
        }
    else:
        risk_card = {
            'href': get_shell_route_url('students'),
            'card_class': 'is-risk',
            'indicator_class': 'is-risk',
            'kicker': 'Risco',
            'value': 0,
            'indicator': 'Estável',
            'copy': 'Rotina limpa. O box está funcionando bem e você pode confiar no ritmo.',
        }

    return [emergency_card, urgency_card, risk_card]


def build_dashboard_page(*, request_user, role_slug, snapshot, stored_layout_state=None):
    upcoming_sessions = list(snapshot['upcoming_sessions'])
    student_health = list(snapshot['student_health'])
    payment_alerts = list(snapshot['payment_alerts'])
    next_session = upcoming_sessions[0] if upcoming_sessions else None
    actionable_payment_alerts_count = snapshot.get('actionable_payment_alerts_count', 0)
    next_payment_alert = snapshot.get('next_actionable_payment_alert')
    highest_risk_student = next((student for student in student_health if student.total_absences >= 1), None)
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
        'summary': 'Tem gente esperando um retorno seu. Vou te levar até lá.',
    }
    hero = build_page_hero(
        eyebrow='Hoje',
        title='Bom te ver.',
        copy=_build_dashboard_hero_copy(role_slug),
        actions=_build_dashboard_hero_actions(role_slug),
        aria_label='Panorama do dia',
        classes=['operation-hero'],
        data_slot='hero',
        data_panel='dashboard-hero',
    )
    dashboard_layout = build_dashboard_layout(role_slug, stored_layout_state=stored_layout_state)

    return build_page_payload(
        context={
            'page_key': 'dashboard',
            'title': 'Dashboard do box',
            'subtitle': 'Tudo o que você precisa, no tempo certo.',
            'mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
            'role_slug': role_slug,
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons_from_focus(
                focus=execution_focus,
                pending=pending_focus,
                scope='dashboard-reception' if role_slug == ROLE_RECEPTION else 'dashboard',
            ),
        },
        data={
            **snapshot,
            'hero': hero,
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

