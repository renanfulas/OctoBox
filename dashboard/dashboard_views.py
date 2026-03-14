"""
ARQUIVO: view do dashboard principal.

POR QUE ELE EXISTE:
- centraliza a camada HTTP do painel principal do sistema no app real dashboard.

O QUE ESTE ARQUIVO FAZ:
1. injeta o papel atual do usuario no painel.
2. consome o snapshot consolidado do dashboard.

PONTOS CRITICOS:
- alteracoes erradas aqui podem quebrar o painel principal ou o layout autenticado.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from access.roles import ROLE_DEFINITIONS, ROLE_RECEPTION, get_user_capabilities, get_user_role
from access.shell_actions import build_shell_action_buttons
from shared_support.page_payloads import attach_page_payload, build_page_assets, build_page_payload
from .dashboard_snapshot_queries import build_dashboard_snapshot


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
        'copy': 'Vá direto para a fila de cobrança operacional e resolva o caixa curto no contexto do atendimento.',
        'href': '/operacao/recepcao/#reception-payment-board',
    },
    {
        'eyebrow': 'Acao rapida',
        'title': 'Ler a grade do turno',
        'copy': 'Abra a agenda para responder horário, coach e ocupação sem cair na gestão administrativa da grade.',
        'href': '/grade-aulas/',
    },
]


def _build_dashboard_hero_actions(role_slug):
    if role_slug == ROLE_RECEPTION:
        return [
            {'label': 'Abrir balcao da recepcao', 'href': '/operacao/recepcao/', 'kind': 'primary'},
            {'label': 'Novo aluno', 'href': '/alunos/novo/', 'kind': 'secondary'},
            {'label': 'Abrir grade', 'href': '/grade-aulas/', 'kind': 'secondary'},
        ]

    return [
        {'label': 'Abrir alunos', 'href': '/alunos/', 'kind': 'primary'},
        {'label': 'Abrir financeiro', 'href': '/financeiro/', 'kind': 'secondary'},
        {'label': 'Abrir grade', 'href': '/grade-aulas/', 'kind': 'secondary'},
    ]


def _build_dashboard_hero_copy(role_slug):
    if role_slug == ROLE_RECEPTION:
        return 'Chegada, agenda e caixa curto para abrir o turno.'

    return 'Pressao do dia, fila sensivel e proximo passo.'


def _build_dashboard_execution_focus(role_slug, *, next_session, next_payment_alert, highest_risk_student):
    finance_label = 'Comece pela fila que bate antes'
    finance_summary = (
        f"{next_payment_alert.student.full_name} aparece como primeiro atraso e deve abrir a rodada de cobranca antes que o risco fique invisivel."
        if next_payment_alert else
        'Sem atraso critico no topo da fila agora, entao a cobranca pode ser revisada sem pressa imediata.'
    )
    finance_href = '#dashboard-finance-board'
    finance_href_label = 'Ver alertas financeiros'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Comece pelo caixa curto do turno'
        finance_summary = (
            f"{next_payment_alert.student.full_name} aparece como primeira cobranca atrasada e pode pedir abordagem de balcao ainda hoje."
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
                f"{highest_risk_student.full_name} lidera o risco atual com {highest_risk_student.total_absences} falta(s), entao vale validar retencao antes de perder temperatura da base."
                if highest_risk_student else
                ('Sem dados de risco suficientes no momento, entao a base ainda nao pede leitura de retencao por ausencia.' if role_slug != ROLE_RECEPTION else 'Nenhum aluno aparece com sinal claro de esfriamento agora, entao a recepcao pode seguir com foco em chegada, agenda e caixa curto.')
            ),
            'pill_class': 'warning' if highest_risk_student else 'success',
            'href': '#dashboard-risk-board',
            'href_label': 'Ver risco por aluno' if role_slug != ROLE_RECEPTION else 'Ver alunos que pedem cuidado',
        },
    ]


def _build_dashboard_table_guides(role_slug, *, next_session, next_payment_alert, highest_risk_student):
    finance_label = 'Cobranca que abre o recorte'
    finance_summary = (
        f"Venceu em {next_payment_alert.due_date.strftime('%d/%m/%Y')} e deve ser lido antes dos outros alertas."
        if next_payment_alert else
        'A fila financeira nao esta pressionando o dia neste momento.'
    )
    finance_href = '#dashboard-finance-board'
    finance_href_label = 'Abrir cobranca'

    if role_slug == ROLE_RECEPTION:
        finance_label = 'Caixa curto que abre o turno'
        finance_summary = (
            f"A cobranca de {next_payment_alert.student.full_name} e a melhor abertura para o caixa curto do balcao agora."
            if next_payment_alert else
            'O caixa curto nao esta pressionando o turno neste momento.'
        )
        finance_href = '/operacao/recepcao/#reception-payment-board'
        finance_href_label = 'Abrir fila curta'

    return [
        {
            'label': finance_label,
            'value': next_payment_alert.student.full_name if next_payment_alert else 'Sem atraso critico',
            'summary': finance_summary,
            'href': finance_href,
            'href_label': finance_href_label,
            'pill_class': 'warning' if next_payment_alert else 'success',
        },
        {
            'label': 'Agenda que move a recepcao',
            'value': next_session['object'].title if next_session else 'Sem aula imediata',
            'summary': (
                f"Comece por {next_session['starts_at'].strftime('%d/%m %H:%M')} para ler coach, status e ocupacao mais rapido."
                if next_session else
                'A agenda do recorte atual esta leve e nao deve sequestrar o foco principal.'
            ),
            'href': '#dashboard-sessions-board',
            'href_label': 'Abrir agenda',
            'pill_class': 'info' if next_session else 'accent',
        },
        {
            'label': 'Aluno que pode esfriar',
            'value': highest_risk_student.full_name if highest_risk_student else ('Sem risco mapeado' if role_slug != ROLE_RECEPTION else 'Base estavel'),
            'summary': (
                f"{highest_risk_student.total_absences} falta(s) ja colocam esse aluno no topo da leitura de retencao."
                if highest_risk_student else
                ('Ainda nao ha um aluno liderando risco por ausencia no recorte atual.' if role_slug != ROLE_RECEPTION else 'Nenhum aluno aparece com sinal de esfriamento forte no recorte atual.')
            ),
            'href': '#dashboard-risk-board',
            'href_label': 'Abrir risco' if role_slug != ROLE_RECEPTION else 'Abrir leitura de cuidado',
            'pill_class': 'warning' if highest_risk_student else 'success',
        },
    ]


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        current_role = get_user_role(self.request.user)
        role_slug = getattr(current_role, 'slug', '')
        snapshot = build_dashboard_snapshot(today=today, month_start=month_start, role_slug=role_slug)
        upcoming_sessions = list(snapshot['upcoming_sessions'])
        payment_alerts = list(snapshot['payment_alerts'])
        student_health = list(snapshot['student_health'])

        next_session = upcoming_sessions[0] if upcoming_sessions else None
        next_payment_alert = payment_alerts[0] if payment_alerts else None
        highest_risk_student = next((student for student in student_health if student.total_absences >= 1), None)
        context['current_role'] = current_role
        page_payload = build_page_payload(
            context={
                'page_key': 'dashboard',
                'title': 'Painel principal',
                'subtitle': 'Pressao do dia, fila sensivel e proximo passo numa leitura curta e executavel.',
                'mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
                'role_slug': role_slug,
            },
            shell={
                'shell_action_buttons': build_shell_action_buttons(
                    priority=_build_dashboard_execution_focus(
                        role_slug,
                        next_session=next_session,
                        next_payment_alert=next_payment_alert,
                        highest_risk_student=highest_risk_student,
                    )[0],
                    pending={
                        'href': '/operacao/recepcao/#reception-intake-board' if role_slug == ROLE_RECEPTION else '/alunos/#student-intake-board',
                        'summary': 'Abrir o que segue pendente de entrada, vínculo ou acolhimento antes de esfriar.',
                    },
                    next_action=_build_dashboard_execution_focus(
                        role_slug,
                        next_session=next_session,
                        next_payment_alert=next_payment_alert,
                        highest_risk_student=highest_risk_student,
                    )[1],
                    scope='dashboard-reception' if role_slug == ROLE_RECEPTION else 'dashboard',
                ),
            },
            data={
                **snapshot,
                'dashboard_role_mode': 'reception' if role_slug == ROLE_RECEPTION else 'default',
                'role_capabilities': get_user_capabilities(self.request.user),
                'role_definitions': ROLE_DEFINITIONS,
                'dashboard_hero_copy': _build_dashboard_hero_copy(role_slug),
                'dashboard_hero_actions': _build_dashboard_hero_actions(role_slug),
                'dashboard_quick_actions': RECEPTION_DASHBOARD_QUICK_ACTIONS if role_slug == ROLE_RECEPTION else DASHBOARD_QUICK_ACTIONS,
                'dashboard_execution_focus': _build_dashboard_execution_focus(
                    role_slug,
                    next_session=next_session,
                    next_payment_alert=next_payment_alert,
                    highest_risk_student=highest_risk_student,
                ),
                'dashboard_table_guides': _build_dashboard_table_guides(
                    role_slug,
                    next_session=next_session,
                    next_payment_alert=next_payment_alert,
                    highest_risk_student=highest_risk_student,
                ),
            },
            assets=build_page_assets(css=['css/design-system/operations.css', 'css/design-system/dashboard.css']),
        )
        attach_page_payload(context, payload_key='dashboard_page', payload=page_payload)
        return context