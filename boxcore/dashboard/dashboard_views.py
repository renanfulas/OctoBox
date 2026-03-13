"""
ARQUIVO: view do dashboard principal.

POR QUE ELE EXISTE:
- Centraliza a camada HTTP do painel principal do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Injeta o papel atual do usuario no painel.
2. Consome o snapshot consolidado do dashboard.

PONTOS CRITICOS:
- Alteracoes erradas aqui podem quebrar o painel principal ou o layout autenticado.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from access.roles import ROLE_DEFINITIONS, get_user_capabilities, get_user_role
from .dashboard_snapshot_queries import build_dashboard_snapshot


DASHBOARD_QUICK_ACTIONS = [
    {
        'eyebrow': 'Ação rápida',
        'title': 'Novo intake / aluno',
        'copy': 'Abra o fluxo leve para converter contato em aluno com matrícula e cobrança inicial no mesmo passo.',
        'href': '/alunos/novo/',
    },
    {
        'eyebrow': 'Ação rápida',
        'title': 'Marcar presença',
        'copy': 'Entre na rotina do coach para check-in, check-out e leitura viva da operação de treino.',
        'href': '/operacao/coach/',
    },
    {
        'eyebrow': 'Ação rápida',
        'title': 'Gerar cobrança',
        'copy': 'Vá direto para o centro financeiro e priorize vencidos, ticket médio e carteira ativa.',
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
        context.update(build_dashboard_snapshot(today=today, month_start=month_start))
        context['current_role'] = current_role
        context['role_capabilities'] = get_user_capabilities(self.request.user)
        context['role_definitions'] = ROLE_DEFINITIONS
        context['dashboard_quick_actions'] = DASHBOARD_QUICK_ACTIONS
        return context