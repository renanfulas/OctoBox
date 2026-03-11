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

from boxcore.access.roles import ROLE_DEFINITIONS, get_user_capabilities, get_user_role
from .dashboard_snapshot_queries import build_dashboard_snapshot


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
        return context