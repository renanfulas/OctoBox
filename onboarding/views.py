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

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from shared_support.page_payloads import attach_page_payload

from .forms import IntakeQuickCreateForm
from .intake_context import (
    build_intake_center_context,
    build_intake_search_index_payload,
    parse_non_negative_int,
)
from .intake_dispatcher import dispatch_intake_center_post
from .queries import build_intake_center_snapshot


INTAKE_SEARCH_BOOTSTRAP_LIMIT = 24
INTAKE_SEARCH_PAGE_LIMIT = 50


class IntakeCenterView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)
    template_name = 'onboarding/intake_center.html'

    PANEL_QUEUE = 'tab-intake-queue'
    PANEL_CREATE_LEAD = 'tab-intake-create-lead'
    PANEL_CREATE_INTAKE = 'tab-intake-create-intake'

    def _get_current_role(self):
        return get_user_role(self.request.user)

    def _get_current_role_slug(self):
        return getattr(self._get_current_role(), 'slug', '')

    def _get_active_panel(self):
        panel = self.request.GET.get('panel', '').strip()
        allowed_panels = {
            self.PANEL_QUEUE,
            'tab-intake-source',
            'tab-intake-filters',
            self.PANEL_CREATE_LEAD,
            self.PANEL_CREATE_INTAKE,
        }
        return panel if panel in allowed_panels else self.PANEL_QUEUE

    def _get_create_form_prefix(self, entry_kind):
        return 'lead-create' if entry_kind == 'lead' else 'intake-create'

    def _build_create_form(self, *, entry_kind, bound_data=None):
        prefix = self._get_create_form_prefix(entry_kind)
        return IntakeQuickCreateForm(bound_data, prefix=prefix) if bound_data is not None else IntakeQuickCreateForm(prefix=prefix)

    def _get_quick_create_success_url(self, entry_kind):
        panel = self.PANEL_CREATE_LEAD if entry_kind == 'lead' else self.PANEL_CREATE_INTAKE
        return f"{reverse('intake-center')}?panel={panel}"

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
        snapshot = kwargs.get('snapshot') or self._build_snapshot()
        extra_context = build_intake_center_context(
            request=self.request,
            snapshot=snapshot,
            current_role_slug=self._get_current_role_slug(),
            active_panel=kwargs.get('active_panel') or self._get_active_panel(),
            lead_create_form=kwargs.get('lead_create_form') or self._build_create_form(entry_kind='lead'),
            intake_create_form=kwargs.get('intake_create_form') or self._build_create_form(entry_kind='intake'),
            search_bootstrap_limit=INTAKE_SEARCH_BOOTSTRAP_LIMIT,
            search_page_limit=INTAKE_SEARCH_PAGE_LIMIT,
        )
        attach_page_payload(context, payload_key='intake_center_page', payload=extra_context.pop('intake_center_page'))
        context.update(extra_context)
        return context

    def post(self, request, *args, **kwargs):
        return dispatch_intake_center_post(view=self, request=request)


class IntakeSearchIndexPageView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, *args, **kwargs):
        current_role = get_user_role(request.user)
        offset = parse_non_negative_int(request.GET.get('offset'), default=0)
        return JsonResponse(
            build_intake_search_index_payload(
                request=request,
                current_role_slug=getattr(current_role, 'slug', ''),
                offset=offset,
                page_limit=INTAKE_SEARCH_PAGE_LIMIT,
            )
        )


__all__ = ['IntakeCenterView', 'IntakeSearchIndexPageView']
