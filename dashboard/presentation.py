"""
ARQUIVO: presentation do dashboard principal.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem estrutural do painel principal.
- mantem a borda HTTP curta e o contrato da tela explicito.
"""

from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Quem chega',
        'title': 'Novas entradas',
        'copy': 'Tem gente chegando. Vou te mostrar onde ainda da pra criar vinculo.',
        'href': '/entradas/',
    },
    {
        'eyebrow': 'Agenda',
        'title': 'As turmas do dia',
        'copy': 'A agenda esta aqui. Eu cuido da leitura, voce decide o passo.',
        'href': '/grade-aulas/',
    },
    {
        'eyebrow': 'Caixa',
        'title': 'Receita e saude',
        'copy': 'Separei o que entrou e o que ainda pede cuidado. Voce vai saber o que fazer.',
        'href': '/financeiro/',
    },
]


COACH_DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Fila principal',
        'title': 'Rota de entradas',
        'copy': 'Tem gente nova na porta. Vou te mostrar como isso muda o turno.',
        'href': '/entradas/',
    },
    {
        'eyebrow': 'Presenca',
        'title': 'Registrar turma',
        'copy': 'Sua turma esta esperando. Comece por aqui e eu acompanho contigo.',
        'href': '/operacao/coach/',
    },
    {
        'eyebrow': 'Agenda viva',
        'title': 'Turmas em movimento',
        'copy': 'Montei a composicao das turmas pra voce. So confirmar e seguir.',
        'href': '/grade-aulas/',
    },
]


RECEPTION_DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Chegada',
        'title': 'Novo aluno',
        'copy': 'Alguem chegou. Vou te guiar pra ficha ficar pronta rapido.',
        'href': '/alunos/novo/',
    },
    {
        'eyebrow': 'Caixa',
        'title': 'Cobrancas do dia',
        'copy': 'Separei o que precisa sair agora. Pode confiar, esta tudo aqui.',
        'href': '/operacao/recepcao/#reception-payment-board',
    },
    {
        'eyebrow': 'Agenda viva',
        'title': 'Grade do turno',
        'copy': 'Organizei horario, coach e vagas pra voce responder com seguranca.',
        'href': '/grade-aulas/',
    },
]


def _build_dashboard_hero_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return [
            {'label': 'Abrir balcao da recepcao', 'href': '/operacao/recepcao/', 'kind': 'primary'},
            {'label': 'Novo aluno', 'href': '/alunos/novo/', 'kind': 'secondary'},
        ]

    return [
        {'label': 'Abrir alunos', 'href': '/alunos/', 'kind': 'primary'},
        {'label': 'Abrir financeiro', 'href': '/financeiro/', 'kind': 'secondary'},
    ]


def _build_dashboard_hero_copy(role_slug):
    if role_slug == ROLE_RECEPTION:
        return 'Estou aqui com voce. Vamos cuidar do balcao juntos.'

    return 'Estou junto contigo. Vamos olhar o que importa hoje.'


def _build_dashboard_quick_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return RECEPTION_DASHBOARD_QUICK_ACTIONS
    if role_slug == ROLE_COACH:
        return COACH_DASHBOARD_QUICK_ACTIONS
    return DASHBOARD_QUICK_ACTIONS


def _can_register_finance_whatsapp(role_slug):
    return role_slug in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION}


def _build_dashboard_execution_focus(role_slug, *, next_session, next_payment_alert, highest_risk_student, actionable_payment_alerts_count):
    finance_label = 'Cuido do caixa contigo. Comece por aqui'
    finance_summary = (
        f'{actionable_payment_alerts_count} cobranca(s) pedem contato. {next_payment_alert.student.full_name} e o melhor ponto pra comecar. Voce consegue resolver isso.'
        if next_payment_alert else
        'Nenhuma cobranca critica agora. O caixa esta bem e voce pode respirar.'
    )
    finance_href = '/financeiro/'
    finance_href_label = 'Abrir financeiro'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Essa cobranca cabe no seu turno. Vamos juntos'
        finance_summary = (
            f'{actionable_payment_alerts_count} cobranca(s) pedem sua atencao. {next_payment_alert.student.full_name} e quem mais precisa de voce agora.'
            if next_payment_alert else
            'O caixa curto esta tranquilo. Voce esta dando conta.'
        )
        finance_href = '/operacao/recepcao/#reception-payment-board'
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
                f"{next_session['object'].title} e a proxima. Deixei tudo organizado pra voce so confirmar."
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
                f'{highest_risk_student.full_name} sumiu um pouco com {highest_risk_student.total_absences} falta(s). Um contato seu pode trazer de volta. Voce consegue.'
                if highest_risk_student else
                ('A base esta firme. Ninguem mostra sinal de esfriamento. Voce esta cuidando bem.' if role_slug != ROLE_RECEPTION else 'Ninguem precisa de resgate agora. O balcao esta acolhendo bem.')
            ),
            'pill_class': 'warning' if highest_risk_student else 'success',
            'href': '/alunos/',
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
    finance_href = '/operacao/recepcao/#reception-payment-board' if role_slug == ROLE_RECEPTION else '/financeiro/'
    primary_payment_alert = next_payment_alert or (payment_alerts[0] if payment_alerts else None)
    overdue_count = metrics['overdue_payments']

    if actionable_payment_alerts_count > 0 and primary_payment_alert:
        emergency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Emergência',
            'value': actionable_payment_alerts_count,
            'indicator': 'Caixa' if role_slug == ROLE_RECEPTION else 'Urgente',
            'copy': (
                f'{primary_payment_alert.student.full_name} esta esperando contato. Eu te guio: comece por aqui e o caixa agradece.'
                if role_slug != ROLE_RECEPTION else
                f'{primary_payment_alert.student.full_name} precisa do seu cuidado agora. Uma abordagem sua faz toda a diferenca.'
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
                f'{primary_payment_alert.student.full_name} abre a fila. O dinheiro ainda esta ai, so precisa de voce. Vamos resolver juntos.'
                if role_slug != ROLE_RECEPTION else
                f'{primary_payment_alert.student.full_name} abre a fila curta. O caixa respira, mas uma olhada sua agora faz diferenca.'
            ),
        }
    else:
        emergency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Emergência',
            'value': 0,
            'indicator': 'Estavel',
            'copy': (
                'Caixa limpo. Voce esta no controle. Pode seguir com tranquilidade.'
                if role_slug != ROLE_RECEPTION else
                'Tudo certo no caixa do balcao. Voce esta mandando bem.'
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
            'href': '/alunos/',
            'card_class': 'is-base',
            'indicator_class': 'is-base',
            'kicker': 'Urgente',
            'value': highest_risk_student.total_absences,
            'indicator': 'Retencao' if role_slug != ROLE_RECEPTION else 'Cuidado',
            'copy': (
                f'{highest_risk_student.full_name} sumiu um pouco, {highest_risk_student.total_absences} falta(s). Uma mensagem sua pode ser o que faltava pra voltar.'
                if role_slug != ROLE_RECEPTION else
                f'{highest_risk_student.full_name} precisa sentir que alguem notou, {highest_risk_student.total_absences} falta(s). Seu acolhimento pode mudar tudo.'
            ),
        }
    elif pressured_session:
        starts_at_label = timezone.localtime(pressured_session['starts_at']).strftime('%H:%M')
        urgency_card = {
            'href': '#dashboard-sessions-board',
            'card_class': 'is-sessions',
            'indicator_class': 'is-sessions',
            'kicker': 'Urgente',
            'value': pressured_session['occupancy_percent'] or len(upcoming_sessions),
            'indicator': 'Turno',
            'copy': (
                f"{pressured_session['object'].title} esta acontecendo agora. Eu cuido da leitura, voce cuida da equipe."
                if pressured_session['status_label'] == 'Em andamento' else
                f"{pressured_session['object'].title} comeca as {starts_at_label} e precisa de atencao. Vou te levar pra agenda."
            ),
        }
    else:
        urgency_card = {
            'href': '/alunos/',
            'card_class': 'is-base',
            'indicator_class': 'is-base',
            'kicker': 'Urgente',
            'value': 0,
            'indicator': 'Estavel',
            'copy': 'Tudo tranquilo na retencao. A comunidade esta bem e voce pode focar no que quiser.',
        }

    occurrences_count = metrics['occurrences_this_month']
    if occurrences_count > 0 and highest_risk_student:
        risk_card = {
            'href': '/alunos/',
            'card_class': 'is-risk',
            'indicator_class': 'is-risk',
            'kicker': 'Risco',
            'value': occurrences_count,
            'indicator': 'Rotina',
            'copy': (
                f'{occurrences_count} ocorrencia(s) no mes e {highest_risk_student.full_name} com {highest_risk_student.total_absences} falta(s). Eu organizo os dados, voce decide a acao. Juntos resolvemos.'
                if role_slug != ROLE_RECEPTION else
                f'{occurrences_count} ocorrencia(s) no mes e {highest_risk_student.full_name} pede acolhimento. Eu te mostro por onde comecar.'
            ),
        }
    elif occurrences_count > 0:
        risk_card = {
            'href': '/alunos/',
            'card_class': 'is-risk',
            'indicator_class': 'is-risk',
            'kicker': 'Risco',
            'value': occurrences_count,
            'indicator': 'Rotina',
            'copy': 'Algumas ocorrencias apareceram. Vou te ajudar a organizar antes que vire problema.',
        }
    else:
        risk_card = {
            'href': '/alunos/',
            'card_class': 'is-risk',
            'indicator_class': 'is-risk',
            'kicker': 'Risco',
            'value': 0,
            'indicator': 'Estavel',
            'copy': 'Rotina limpa. O box esta funcionando bem e voce pode confiar no ritmo.',
        }

    return [emergency_card, urgency_card, risk_card]


def build_dashboard_page(*, request_user, role_slug, snapshot):
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
        'href': '/operacao/recepcao/#reception-intake-board' if role_slug == ROLE_RECEPTION else '/entradas/#intake-queue-board',
        'summary': 'Tem gente esperando um retorno seu. Vou te levar ate la.',
    }
    hero = build_page_hero(
        eyebrow='Hoje',
        title='Bom te ver.',
        copy=_build_dashboard_hero_copy(role_slug),
        actions=_build_dashboard_hero_actions(role_slug),
        aria_label='Panorama do dia',
        classes=['dashboard-hero'],
        data_slot='hero',
        data_panel='dashboard-hero',
    )

    return build_page_payload(
        context={
            'page_key': 'dashboard',
            'title': 'Dashboard do box',
            'subtitle': 'Tudo o que voce precisa, no tempo certo.',
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
            'dashboard_role_mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
            'dashboard_can_register_finance_whatsapp': _can_register_finance_whatsapp(role_slug),
            'dashboard_quick_actions': _build_dashboard_quick_actions(role_slug),
            'dashboard_execution_focus': execution_focus,
            'dashboard_priority_cards': priority_cards,
        },
        assets=build_page_assets(css=['css/design-system/operations.css', 'css/design-system/dashboard.css', 'css/design-system/neon.css']),
    )

