"""
ARQUIVO: views do guia interno do sistema.

POR QUE ELE EXISTE:
- traduz a arquitetura do projeto para uma visao visual e pedagogica dentro do app real guide.

O QUE ESTE ARQUIVO FAZ:
1. expoe a pagina Mapa do Sistema.
2. organiza modulos, fluxo, pontos de bug e ordem de leitura.
3. entrega uma visao navegavel para manutencao e estudo.

PONTOS CRITICOS:
- a navegacao por papel vem de context processor global e precisa continuar coerente aqui.
- a estrutura exibida aqui deve acompanhar a organizacao real do projeto.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_OWNER
from shared_support.page_payloads import attach_page_payload
from shared_support.operational_settings import set_operational_whatsapp_repeat_block_hours

from .presentation import build_operational_settings_page, build_system_map_page


class SystemMapView(LoginRequiredMixin, TemplateView):
    template_name = 'guide/system-map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_payload = build_system_map_page()
        attach_page_payload(
            context,
            payload_key='system_map_page',
            payload=page_payload,
        )
        return context


class OperationalSettingsView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV)
    template_name = 'guide/operational-settings.html'

    def post(self, request, *args, **kwargs):
        raw_value = request.POST.get('repeat_block_hours', '')
        try:
            set_operational_whatsapp_repeat_block_hours(hours=raw_value, actor=request.user)
        except ValueError:
            messages.error(request, 'Escolha apenas 24h, 12h ou 0h para a janela do WhatsApp.')
        else:
            messages.success(request, 'Janela de bloqueio do WhatsApp atualizada com sucesso.')
        return redirect('operational-settings')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_payload = build_operational_settings_page()
        attach_page_payload(
            context,
            payload_key='operational_settings_page',
            payload=page_payload,
        )
        return context