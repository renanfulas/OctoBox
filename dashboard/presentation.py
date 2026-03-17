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
        'eyebrow': 'Fila principal',
        'title': 'Rota de entradas',
        'copy': 'Ative a fila de novos contatos e veja onde a energia comercial ainda pode virar matricula.',
        'href': '/entradas/',
    },
    {
        'eyebrow': 'Agenda viva',
        'title': 'Turmas em movimento',
        'copy': 'Entre na grade do dia para sentir o ritmo das turmas, ocupacao e resposta do time.',
        'href': '/grade-aulas/',
    },
    {
        'eyebrow': 'Caixa e receita',
        'title': 'Sprint de receita',
        'copy': 'Va direto para caixa, atrasos e receita realizada em uma leitura de performance do negocio.',
        'href': '/financeiro/',
    },
]


COACH_DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Fila principal',
        'title': 'Rota de entradas',
        'copy': 'Veja o que ainda esta em conversa para antecipar impacto no turno, na turma e no acolhimento.',
        'href': '/entradas/',
    },
    {
        'eyebrow': 'Execucao do turno',
        'title': 'Marcar presenca',
        'copy': 'Entre na rotina do coach para registrar presenca e manter a turma com ritmo e energia.',
        'href': '/operacao/coach/',
    },
    {
        'eyebrow': 'Agenda viva',
        'title': 'Turmas em movimento',
        'copy': 'Abra a agenda para revisar o turno e conferir a composicao das turmas em andamento.',
        'href': '/grade-aulas/',
    },
]


RECEPTION_DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Atendimento',
        'title': 'Novo aluno no balcao',
        'copy': 'Abra o fluxo de cadastro curto para transformar chegada em ficha pronta sem perder ritmo no balcao.',
        'href': '/alunos/novo/',
    },
    {
        'eyebrow': 'Caixa curto',
        'title': 'Cobrancas do balcao',
        'copy': 'Va direto para a fila operacional e resolva o caixa curto no calor do atendimento.',
        'href': '/operacao/recepcao/#reception-payment-board',
    },
    {
        'eyebrow': 'Agenda viva',
        'title': 'Grade do turno',
        'copy': 'Abra a agenda para responder horario, coach e ocupacao sem cair na gestao completa da grade.',
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
        return 'Chegada, agenda e caixa curto em um painel rapido, energico e imediatamente util para o balcao.'

    return 'Receita, agenda e presenca em um pulso unico para decidir com clareza e energia.'


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
        f'{actionable_payment_alerts_count} cobranca(s) pedem acao agora. {next_payment_alert.student.full_name} e o primeiro caso para abrir a rodada antes que o atraso cresca.'
        if next_payment_alert else
        'Nenhuma cobranca com contato liberado pede acao imediata agora.'
    )
    finance_href = '/financeiro/'
    finance_href_label = 'Abrir financeiro'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Comece pela cobranca que cabe no balcao'
        finance_summary = (
            f'{actionable_payment_alerts_count} cobranca(s) pedem acao agora. {next_payment_alert.student.full_name} e o primeiro caso e pode pedir abordagem de balcao hoje.'
            if next_payment_alert else
            'Nenhuma cobranca com contato liberado pressiona o caixa curto agora.'
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
            'label': 'Depois confirme a agenda de hoje',
            'chip_label': 'Aulas',
            'summary': (
                f"{next_session['object'].title} e a proxima aula e ja mostra o que vai ocupar equipe, coach e recepcao."
                if next_session else
                'Sem aulas proximas neste recorte, a agenda nao e o ponto mais sensivel desta rodada.'
            ),
            'pill_class': 'info' if next_session else 'accent',
            'href': '#dashboard-sessions-board',
            'href_label': 'Abrir agenda do dia',
        },
        {
            'label': 'Feche com o risco de perda' if role_slug != ROLE_RECEPTION else 'Feche com quem pede acolhimento',
            'chip_label': 'Risco' if role_slug != ROLE_RECEPTION else 'Retencao',
            'summary': (
                f'{highest_risk_student.full_name} lidera o risco atual com {highest_risk_student.total_absences} falta(s) e merece contato antes de esfriar de vez.'
                if highest_risk_student else
                ('Sem sinais fortes de perda neste momento, entao a base nao pede leitura de retencao agora.' if role_slug != ROLE_RECEPTION else 'Nenhum aluno aparece com sinal claro de esfriamento agora.')
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
        urgency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Urgencia',
            'value': actionable_payment_alerts_count,
            'indicator': 'Caixa' if role_slug == ROLE_RECEPTION else 'Urgente',
            'copy': (
                f'{primary_payment_alert.student.full_name} pode receber contato agora. Essa e a pendencia que mais encosta no caixa do box hoje.'
                if role_slug != ROLE_RECEPTION else
                f'{primary_payment_alert.student.full_name} cabe em abordagem de balcao agora. Essa e a pendencia mais quente para proteger o caixa curto.'
            ),
        }
    elif overdue_count > 0 and primary_payment_alert:
        urgency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Urgencia',
            'value': overdue_count,
            'indicator': 'Controle',
            'copy': (
                f'{primary_payment_alert.student.full_name} abre a fila de cobrancas mapeadas. O dinheiro ainda nao esta perdido, mas a leitura precisa acontecer agora.'
                if role_slug != ROLE_RECEPTION else
                f'{primary_payment_alert.student.full_name} abre a fila curta de cobrancas. O caixa ainda respira, mas ja pede leitura de balcao.'
            ),
        }
    else:
        urgency_card = {
            'href': finance_href,
            'card_class': 'is-finance',
            'indicator_class': 'is-finance',
            'kicker': 'Urgencia',
            'value': 0,
            'indicator': 'Estavel',
            'copy': (
                'Sem pendencia financeira critica no recorte atual. O caixa pede rotina, nao resposta imediata.'
                if role_slug != ROLE_RECEPTION else
                'Sem cobranca curta critica no recorte atual. O caixa do balcao esta sob controle agora.'
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
        emergency_card = {
            'href': '/alunos/',
            'card_class': 'is-base',
            'indicator_class': 'is-base',
            'kicker': 'Emergencia',
            'value': highest_risk_student.total_absences,
            'indicator': 'Retencao' if role_slug != ROLE_RECEPTION else 'Cuidado',
            'copy': (
                f'{highest_risk_student.full_name} ja soma {highest_risk_student.total_absences} falta(s). Isso ainda nao bate o caixa agora, mas aproxima perda de receita se ficar sem abordagem.'
                if role_slug != ROLE_RECEPTION else
                f'{highest_risk_student.full_name} ja soma {highest_risk_student.total_absences} falta(s). Sem acolhimento rapido, o balcao sente a perda de vinculo antes do caixa perceber.'
            ),
        }
    elif pressured_session:
        starts_at_label = timezone.localtime(pressured_session['starts_at']).strftime('%H:%M')
        emergency_card = {
            'href': '#dashboard-sessions-board',
            'card_class': 'is-sessions',
            'indicator_class': 'is-sessions',
            'kicker': 'Emergencia',
            'value': pressured_session['occupancy_percent'] or len(upcoming_sessions),
            'indicator': 'Turno',
            'copy': (
                f"{pressured_session['object'].title} ja esta em andamento e pressiona equipe, experiencia e resposta do turno."
                if pressured_session['status_label'] == 'Em andamento' else
                f"{pressured_session['object'].title} comeca as {starts_at_label} em pressao operacional real. Vale entrar na agenda antes que a experiencia degrade."
            ),
        }
    else:
        emergency_card = {
            'href': '/alunos/',
            'card_class': 'is-base',
            'indicator_class': 'is-base',
            'kicker': 'Emergencia',
            'value': 0,
            'indicator': 'Estavel',
            'copy': 'Nenhuma pendencia emergente ligada a retencao ou experiencia aparece no recorte atual.',
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
                f'{occurrences_count} ocorrencia(s) ja apareceram no mes e {highest_risk_student.full_name} soma {highest_risk_student.total_absences} falta(s). Vale organizar a base antes do ruido virar evasao.'
                if role_slug != ROLE_RECEPTION else
                f'{occurrences_count} ocorrencia(s) ja apareceram no mes e {highest_risk_student.full_name} pede acolhimento. Vale organizar a rotina antes do balcao absorver o caos.'
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
            'copy': 'As ocorrencias do mes mostram que a rotina esta pedindo mais organizacao antes que o ruido vire retrabalho.',
        }
    else:
        risk_card = {
            'href': '/alunos/',
            'card_class': 'is-risk',
            'indicator_class': 'is-risk',
            'kicker': 'Risco',
            'value': 0,
            'indicator': 'Estavel',
            'copy': 'Sem sinal forte de desorganizacao no recorte imediato. A rotina do box esta respirando com previsibilidade.',
        }

    return [urgency_card, emergency_card, risk_card]


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
        'summary': 'Abrir o que segue pendente de entrada, vinculo ou acolhimento antes de esfriar.',
    }
    hero = build_page_hero(
        eyebrow='Dashboard do dia',
        title='Seu box em alta performance.',
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
            'subtitle': 'Negocio e comunidade em uma leitura clara, energica e pronta para acao.',
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
        assets=build_page_assets(css=['css/design-system/operations.css', 'css/design-system/dashboard.css']),
    )

