"""
ARQUIVO: presentation do dashboard principal.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem estrutural do painel principal.
- mantem a borda HTTP curta e o contrato da tela explicito.
"""

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload


DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Acao rapida',
        'title': 'Ver entradas em aberto',
        'copy': 'Abra a fila de novos contatos e veja quem ainda pede resposta, vínculo ou fechamento.',
        'href': '/entradas/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Abrir aulas do dia',
        'copy': 'Abra a agenda do turno para responder rápido sobre horário, coach e ocupação.',
        'href': '/grade-aulas/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Abrir financeiro',
        'copy': 'Vá direto para atrasos, receita do mês e pressão de cobrança sem procurar em outra área.',
        'href': '/financeiro/',
    },
]


COACH_DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Acao rapida',
        'title': 'Ver entradas em aberto',
        'copy': 'Veja o que ainda está em conversa para antecipar impacto no turno e no acolhimento.',
        'href': '/entradas/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Marcar presenca',
        'copy': 'Entre na rotina do coach para registrar presença e manter a turma sob controle.',
        'href': '/operacao/coach/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Abrir aulas do dia',
        'copy': 'Abra a agenda para revisar o turno e conferir a composição das turmas.',
        'href': '/grade-aulas/',
    },
]


RECEPTION_DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Acao rapida',
        'title': 'Novo aluno no balcao',
        'copy': 'Abra o fluxo de cadastro curto para transformar a chegada em ficha pronta sem travar o balcão.',
        'href': '/alunos/novo/',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Ver cobrancas do balcao',
        'copy': 'Vá direto para a fila de cobrança operacional e resolva o caixa curto no contexto do atendimento.',
        'href': '/operacao/recepcao/#reception-payment-board',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Ler a grade do turno',
        'copy': 'Abra a agenda para responder horário, coach e ocupação sem cair na gestão completa da grade.',
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
        return 'Comece por chegada, agenda e cobrança curta sem sobrecarregar o balcão.'

    return 'Veja primeiro caixa, agenda e risco da base para decidir sem excesso de leitura.'


def _build_dashboard_quick_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return RECEPTION_DASHBOARD_QUICK_ACTIONS
    if role_slug == ROLE_COACH:
        return COACH_DASHBOARD_QUICK_ACTIONS
    return DASHBOARD_QUICK_ACTIONS


def _can_register_finance_whatsapp(role_slug):
    return role_slug in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION}


def _build_dashboard_execution_focus(role_slug, *, next_session, next_payment_alert, highest_risk_student, actionable_payment_alerts_count):
    finance_label = 'Comece pela fila que bate antes'
    finance_summary = (
        f'{actionable_payment_alerts_count} cobrança(s) pedem ação agora. {next_payment_alert.student.full_name} é o primeiro caso para abrir a rodada antes que o atraso cresça.'
        if next_payment_alert else
        'Nenhuma cobrança com contato liberado pede ação imediata agora.'
    )
    finance_href = '#dashboard-finance-board'
    finance_href_label = 'Abrir cobrancas em atraso'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Comece pela cobrança que cabe no balcão'
        finance_summary = (
            f'{actionable_payment_alerts_count} cobrança(s) pedem ação agora. {next_payment_alert.student.full_name} é o primeiro caso e pode pedir abordagem de balcão hoje.'
            if next_payment_alert else
            'Nenhuma cobrança com contato liberado pressiona o caixa curto agora.'
        )
        finance_href = '/operacao/recepcao/#reception-payment-board'
        finance_href_label = 'Abrir cobrancas do balcao'

    return [
        {
            'label': finance_label,
            'count': actionable_payment_alerts_count,
            'summary': finance_summary,
            'pill_class': 'warning' if next_payment_alert else 'success',
            'href': finance_href,
            'href_label': finance_href_label,
        },
        {
            'label': 'Depois confirme a agenda de hoje',
            'summary': (
                f"{next_session['object'].title} é a próxima aula e já mostra o que vai ocupar equipe, coach e recepção."
                if next_session else
                'Sem aulas próximas neste recorte, a agenda não é o ponto mais sensível desta rodada.'
            ),
            'pill_class': 'info' if next_session else 'accent',
            'href': '#dashboard-sessions-board',
            'href_label': 'Abrir agenda do dia',
        },
        {
            'label': 'Feche com o risco de perda' if role_slug != ROLE_RECEPTION else 'Feche com quem pede acolhimento',
            'summary': (
                f'{highest_risk_student.full_name} lidera o risco atual com {highest_risk_student.total_absences} falta(s) e merece contato antes de esfriar de vez.'
                if highest_risk_student else
                ('Sem sinais fortes de perda neste momento, então a base não pede leitura de retenção agora.' if role_slug != ROLE_RECEPTION else 'Nenhum aluno aparece com sinal claro de esfriamento agora.')
            ),
            'pill_class': 'warning' if highest_risk_student else 'success',
            'href': '#dashboard-risk-board',
            'href_label': 'Abrir risco por aluno' if role_slug != ROLE_RECEPTION else 'Abrir alunos que pedem cuidado',
        },
    ]


def build_dashboard_page(*, request_user, role_slug, snapshot):
    upcoming_sessions = list(snapshot['upcoming_sessions'])
    payment_alerts = list(snapshot['payment_alerts'])
    student_health = list(snapshot['student_health'])
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
    pending_focus = {
        'href': '/operacao/recepcao/#reception-intake-board' if role_slug == ROLE_RECEPTION else '/entradas/#intake-queue-board',
        'summary': 'Abrir o que segue pendente de entrada, vinculo ou acolhimento antes de esfriar.',
    }
    hero = build_page_hero(
        eyebrow='Leitura executiva do dia',
        title='Seu box em tres decisoes.',
        copy=_build_dashboard_hero_copy(role_slug),
        actions=_build_dashboard_hero_actions(role_slug),
        side={
            'kind': 'stats-panel',
            'eyebrow': 'Resumo imediato',
            'copy': 'Quatro números para ler base, agenda, atrasos e receita sem abrir outra tela.',
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
            'title': 'Seu box em 3 decisoes',
            'subtitle': 'Caixa, agenda e risco da base em uma leitura curta.',
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
            'dashboard_can_register_finance_whatsapp': _can_register_finance_whatsapp(role_slug),
            'dashboard_quick_actions': _build_dashboard_quick_actions(role_slug),
            'dashboard_execution_focus': execution_focus,
        },
        assets=build_page_assets(css=['css/design-system/operations.css', 'css/design-system/dashboard.css']),
    )