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

from access.roles import ROLE_DEFINITIONS, get_user_capabilities, get_user_role
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


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        current_role = get_user_role(self.request.user)
        snapshot = build_dashboard_snapshot(today=today, month_start=month_start)
        upcoming_sessions = list(snapshot['upcoming_sessions'])
        payment_alerts = list(snapshot['payment_alerts'])
        student_health = list(snapshot['student_health'])

        next_session = upcoming_sessions[0] if upcoming_sessions else None
        next_payment_alert = payment_alerts[0] if payment_alerts else None
        highest_risk_student = student_health[0] if student_health else None

        context.update(snapshot)
        context['current_role'] = current_role
        context['role_capabilities'] = get_user_capabilities(self.request.user)
        context['role_definitions'] = ROLE_DEFINITIONS
        context['dashboard_quick_actions'] = DASHBOARD_QUICK_ACTIONS
        context['dashboard_execution_focus'] = [
            {
                'label': 'Comece pela fila que bate antes',
                'summary': (
                    f"{next_payment_alert.student.full_name} aparece como primeiro atraso e deve abrir a rodada de cobranca antes que o risco fique invisivel."
                    if next_payment_alert else
                    'Sem atraso critico no topo da fila agora, entao a cobranca pode ser revisada sem pressa imediata.'
                ),
                'pill_class': 'warning' if next_payment_alert else 'success',
                'href': '#dashboard-finance-board',
                'href_label': 'Ver alertas financeiros',
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
                'label': 'Feche com o risco de esfriamento',
                'summary': (
                    f"{highest_risk_student.full_name} lidera o risco atual com {highest_risk_student.total_absences} falta(s), entao vale validar retencao antes de perder temperatura da base."
                    if highest_risk_student else
                    'Sem dados de risco suficientes no momento, entao a base ainda nao pede leitura de retencao por ausencia.'
                ),
                'pill_class': 'warning' if highest_risk_student and highest_risk_student.total_absences >= 1 else 'success',
                'href': '#dashboard-risk-board',
                'href_label': 'Ver risco por aluno',
            },
        ]
        context['dashboard_table_guides'] = [
            {
                'label': 'Cobranca que abre o recorte',
                'value': next_payment_alert.student.full_name if next_payment_alert else 'Sem atraso critico',
                'summary': (
                    f"Venceu em {next_payment_alert.due_date.strftime('%d/%m/%Y')} e deve ser lido antes dos outros alertas."
                    if next_payment_alert else
                    'A fila financeira nao esta pressionando o dia neste momento.'
                ),
                'href': '#dashboard-finance-board',
                'href_label': 'Abrir cobranca',
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
                'value': highest_risk_student.full_name if highest_risk_student else 'Sem risco mapeado',
                'summary': (
                    f"{highest_risk_student.total_absences} falta(s) ja colocam esse aluno no topo da leitura de retencao."
                    if highest_risk_student else
                    'Ainda nao ha um aluno liderando risco por ausencia no recorte atual.'
                ),
                'href': '#dashboard-risk-board',
                'href_label': 'Abrir risco',
                'pill_class': 'warning' if highest_risk_student and highest_risk_student.total_absences >= 1 else 'success',
            },
        ]
        return context