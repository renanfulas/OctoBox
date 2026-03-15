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

from access.roles import get_user_role
from shared_support.page_payloads import attach_page_payload
from .presentation import build_dashboard_page
from .dashboard_snapshot_queries import build_dashboard_snapshot


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        current_role = get_user_role(self.request.user)
        role_slug = getattr(current_role, 'slug', '')
        snapshot = build_dashboard_snapshot(today=today, month_start=month_start, role_slug=role_slug)
        context['current_role'] = current_role
        page_payload = build_dashboard_page(
            request_user=self.request.user,
            role_slug=role_slug,
            snapshot=snapshot,
        )
        attach_page_payload(context, payload_key='dashboard_page', payload=page_payload)
        return context