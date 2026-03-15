"""
ARQUIVO: views da Central de Intake.

POR QUE ELE EXISTE:
- Publica a casca HTTP da area propria de entradas provisórias.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza a Central de Intake.
2. Respeita permissao por papel.
3. Anexa page payload no contrato compartilhado do front.

PONTOS CRITICOS:
- Essa tela vira o destino canonico de links globais ligados a intake.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from shared_support.page_payloads import attach_page_payload

from .forms import IntakeQueueActionForm
from .facade import run_intake_queue_action
from .presentation import build_intake_center_page
from .queries import build_intake_center_snapshot


class IntakeCenterView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)
    template_name = 'onboarding/intake_center.html'

    def _get_current_role(self):
        return get_user_role(self.request.user)

    def _get_current_role_slug(self):
        return getattr(self._get_current_role(), 'slug', '')

    def _get_filter_params(self):
        if self.request.method == 'POST':
            return self.request.POST.copy()
        return self.request.GET

    def _build_snapshot(self):
        params = self.request.GET if self.request.method == 'GET' else self.request.POST
        params = params.copy()
        params.pop('intake_id', None)
        params.pop('action', None)
        params.pop('return_query', None)
        return build_intake_center_snapshot(params=params, actor_role_slug=self._get_current_role_slug())

    def _get_success_url(self, return_query=''):
        url = reverse('intake-center')
        query_string = (return_query or '').strip()
        return f'{url}?{query_string}' if query_string else url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_role = self._get_current_role()
        page_payload = build_intake_center_page(
            snapshot=kwargs.get('snapshot') or self._build_snapshot(),
            current_role_slug=getattr(current_role, 'slug', ''),
        )
        attach_page_payload(context, payload_key='intake_center_page', payload=page_payload)
        return context

    def post(self, request, *args, **kwargs):
        role_slug = self._get_current_role_slug()
        if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
            messages.error(request, 'Seu papel atual pode consultar a central, mas nao executar a fila por esta tela.')
            return redirect(self._get_success_url())

        form = IntakeQueueActionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A acao de intake nao foi entendida. Revise a fila e tente novamente.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))

        try:
            with transaction.atomic():
                result = run_intake_queue_action(
                    actor=request.user,
                    intake_id=form.cleaned_data['intake_id'],
                    action=form.cleaned_data['action'],
                )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, result.message)

        return redirect(self._get_success_url(form.cleaned_data.get('return_query', '')))


__all__ = ['IntakeCenterView']