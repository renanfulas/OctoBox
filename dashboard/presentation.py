"""
ARQUIVO: presentation do dashboard principal.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem estrutural do painel principal.
- mantem a borda HTTP curta e o contrato da tela explicito.
"""

from access.roles import ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Acao rapida',
        'title': 'Novo intake / aluno',
        'copy': 'Abra o fluxo leve para converter contato em aluno com matricula e cobranca inicial no mesmo passo.',
        'href': '/alunos/novo/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Marcar presenca',
        'copy': 'Entre na rotina do coach para check-in, check-out e leitura viva da operacao de treino.',
        'href': '/operacao/coach/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Gerar cobranca',
        'copy': 'Va direto para o centro financeiro e priorize vencidos, ticket medio e carteira ativa.',
        'href': '/financeiro/',
    },
]


RECEPTION_DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Acao rapida',
        'title': 'Novo aluno no balcao',
        'copy': 'Abra o fluxo leve para converter a chegada em ficha pronta sem sair do compasso da Recepcao.',
        'href': '/alunos/novo/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Abrir fila curta da Recepcao',
        'copy': 'Va direto para a fila de cobranca operacional e resolva o caixa curto no contexto do atendimento.',
        'href': '/operacao/recepcao/#reception-payment-board',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Ler a grade do turno',
        'copy': 'Abra a agenda para responder horario, coach e ocupacao sem cair na gestao administrativa da grade.',
        'href': '/grade-aulas/',
    },
]


def _build_dashboard_hero_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return [
            {'label': 'Abrir balcao da recepcao', 'href': '/operacao/recepcao/', 'kind': 'primary'},
            {'label': 'Novo aluno', 'href': '/alunos/novo/', 'kind': 'secondary'},
            {'label': 'Abrir aulas', 'href': '/grade-aulas/', 'kind': 'secondary'},
        ]

    return [
        {'label': 'Abrir alunos', 'href': '/alunos/', 'kind': 'primary'},
        {'label': 'Abrir financeiro', 'href': '/financeiro/', 'kind': 'secondary'},
        {'label': 'Abrir aulas', 'href': '/grade-aulas/', 'kind': 'secondary'},
    ]


def _build_dashboard_hero_copy(role_slug):
    if role_slug == ROLE_RECEPTION:
        return 'Chegada, agenda e caixa curto para abrir o turno.'

    return 'Pressao do dia, fila sensivel e proximo passo.'


def _build_dashboard_execution_focus(role_slug, *, next_session, next_payment_alert, highest_risk_student):
    finance_label = 'Comece pela fila que bate antes'
    finance_summary = (
        f'{next_payment_alert.student.full_name} aparece como primeiro atraso e deve abrir a rodada de cobranca antes que o risco fique invisivel.'
        if next_payment_alert else
        'Sem atraso critico no topo da fila agora, entao a cobranca pode ser revisada sem pressa imediata.'
    )
    finance_href = '#dashboard-finance-board'
    finance_href_label = 'Ver alertas financeiros'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Comece pelo caixa curto do turno'
        finance_summary = (
            f'{next_payment_alert.student.full_name} aparece como primeira cobranca atrasada e pode pedir abordagem de balcao ainda hoje.'
            if next_payment_alert else
            'Sem cobranca critica na frente da fila agora, entao o balcao pode priorizar chegada e agenda sem pressao de caixa imediato.'
        )
        finance_href = '/operacao/recepcao/#reception-payment-board'
        finance_href_label = 'Abrir fila curta da Recepcao'

    return [
        {
            'label': finance_label,
            'summary': finance_summary,
            'pill_class': 'warning' if next_payment_alert else 'success',
            'href': finance_href,
            'href_label': finance_href_label,
        },
        {
            'label': 'Depois olhe o que movimenta o turno',
            'summary': (
                f"{next_session['object'].title} abre a agenda visivel e ajuda a alinhar coach, recepcao e ocupacao sem ler a tabela inteira."
                if next_session else
                'Sem aulas proximas no recorte atual, entao a agenda nao e o ponto mais sensivel desta rodada.'
            ),
            'pill_class': 'info' if next_session else 'accent',
            'href': '#dashboard-sessions-board',
            'href_label': 'Ver proximas aulas',
        },
        {
            'label': 'Feche com o risco de esfriamento' if role_slug != ROLE_RECEPTION else 'Feche com quem pode pedir acolhimento',
            'summary': (
                f'{highest_risk_student.full_name} lidera o risco atual com {highest_risk_student.total_absences} falta(s), entao vale validar retencao antes de perder temperatura da base.'
                if highest_risk_student else
                ('Sem dados de risco suficientes no momento, entao a base ainda nao pede leitura de retencao por ausencia.' if role_slug != ROLE_RECEPTION else 'Nenhum aluno aparece com sinal claro de esfriamento agora, entao a recepcao pode seguir com foco em chegada, agenda e caixa curto.')
            ),
            'pill_class': 'warning' if highest_risk_student else 'success',
            'href': '#dashboard-risk-board',
            'href_label': 'Ver risco por aluno' if role_slug != ROLE_RECEPTION else 'Ver alunos que pedem cuidado',
        },
    ]


def build_dashboard_page(*, request_user, role_slug, snapshot):
    upcoming_sessions = list(snapshot['upcoming_sessions'])
    payment_alerts = list(snapshot['payment_alerts'])
    student_health = list(snapshot['student_health'])
    next_session = upcoming_sessions[0] if upcoming_sessions else None
    next_payment_alert = payment_alerts[0] if payment_alerts else None
    highest_risk_student = next((student for student in student_health if student.total_absences >= 1), None)
    execution_focus = _build_dashboard_execution_focus(
        role_slug,
        next_session=next_session,
        next_payment_alert=next_payment_alert,
        highest_risk_student=highest_risk_student,
    )
    pending_focus = {
        'href': '/operacao/recepcao/#reception-intake-board' if role_slug == ROLE_RECEPTION else '/alunos/#student-intake-board',
        'summary': 'Abrir o que segue pendente de entrada, vinculo ou acolhimento antes de esfriar.',
    }
    hero = build_page_hero(
        eyebrow='Leitura central do dia',
        title='O que pede acao agora.',
        copy=_build_dashboard_hero_copy(role_slug),
        actions=_build_dashboard_hero_actions(role_slug),
        side={
            'kind': 'stats-panel',
            'eyebrow': 'Leitura instantanea',
            'copy': 'Quatro numeros sobre base, agenda e cobranca.',
            'stats': snapshot['hero_stats'],
            'data_panel': 'dashboard-hero-summary',
        },
        aria_label='Panorama do dia',
        classes=['dashboard-hero'],
        data_slot='hero',
        data_panel='dashboard-hero',
    )

    return build_page_payload(
        context={
            'page_key': 'dashboard',
            'title': 'Painel principal',
            'subtitle': 'Pressao do dia, fila sensivel e proximo passo.',
            'mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
            'role_slug': role_slug,
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons_from_focus(
                focus=execution_focus,
                pending=pending_focus,
                next_action=execution_focus[1],
                scope='dashboard-reception' if role_slug == ROLE_RECEPTION else 'dashboard',
            ),
        },
        data={
            **snapshot,
            'hero': hero,
            'dashboard_role_mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
            'dashboard_quick_actions': RECEPTION_DASHBOARD_QUICK_ACTIONS if role_slug == ROLE_RECEPTION else DASHBOARD_QUICK_ACTIONS,
            'dashboard_execution_focus': execution_focus,
        },
        assets=build_page_assets(css=['css/design-system/operations.css', 'css/design-system/dashboard.css']),
    )