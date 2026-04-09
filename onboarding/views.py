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
from monitoring.lead_attribution_metrics import record_lead_attribution_capture
from onboarding.attribution import build_intake_attribution_payload, normalize_acquisition_channel
from onboarding.models import IntakeStatus
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.page_payloads import attach_page_payload

from .forms import IntakeQueueActionForm, IntakeQuickCreateForm
from .facade import run_intake_queue_action
from .presentation import build_intake_center_page
from .queries import build_intake_center_snapshot


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

    def _get_filter_params(self):
        if self.request.method == 'POST':
            return self.request.POST.copy()
        return self.request.GET

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
        current_role = self._get_current_role()
        page_payload = build_intake_center_page(
            snapshot=kwargs.get('snapshot') or self._build_snapshot(),
            current_role_slug=getattr(current_role, 'slug', ''),
        )
        attach_page_payload(context, payload_key='intake_center_page', payload=page_payload)
        context['active_intake_panel'] = kwargs.get('active_panel') or self._get_active_panel()
        context['lead_create_form'] = kwargs.get('lead_create_form') or self._build_create_form(entry_kind='lead')
        context['intake_create_form'] = kwargs.get('intake_create_form') or self._build_create_form(entry_kind='intake')
        return context

    def post(self, request, *args, **kwargs):
        role_slug = self._get_current_role_slug()
        if request.POST.get('form_kind') == 'quick-create':
            if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
                messages.error(request, 'Seu papel atual pode consultar a central, mas nao cadastrar entradas por esta tela.')
                return redirect(reverse('intake-center'))

            entry_kind = request.POST.get('entry_kind', 'lead').strip().lower()
            if entry_kind not in ('lead', 'intake'):
                entry_kind = 'lead'

            form = self._build_create_form(entry_kind=entry_kind, bound_data=request.POST)
            if not form.is_valid():
                context_kwargs = {
                    'active_panel': self.PANEL_CREATE_LEAD if entry_kind == 'lead' else self.PANEL_CREATE_INTAKE,
                    'lead_create_form': form if entry_kind == 'lead' else self._build_create_form(entry_kind='lead'),
                    'intake_create_form': form if entry_kind == 'intake' else self._build_create_form(entry_kind='intake'),
                }
                return self.render_to_response(self.get_context_data(**context_kwargs))

            with transaction.atomic():
                created_entry = form.save(commit=False)
                created_entry.status = IntakeStatus.NEW
                created_entry.raw_payload = {
                    **(created_entry.raw_payload or {}),
                    **build_intake_attribution_payload(
                        source=created_entry.source,
                        acquisition_channel=form.cleaned_data.get('acquisition_channel', ''),
                        acquisition_detail=form.cleaned_data.get('acquisition_detail', ''),
                        entry_kind=entry_kind,
                        actor_id=getattr(request.user, 'id', None),
                    ),
                }
                created_entry.save()
                record_lead_attribution_capture(
                    entry_kind=entry_kind,
                    operational_source=created_entry.source,
                    acquisition_channel=normalize_acquisition_channel(form.cleaned_data.get('acquisition_channel')),
                )
                publish_manager_stream_event(
                    event_type='intake.updated',
                    meta={
                        'intake_id': created_entry.id,
                        'action': 'quick-create',
                        'status': created_entry.status,
                        'entry_kind': entry_kind,
                        'acquisition_channel': normalize_acquisition_channel(form.cleaned_data.get('acquisition_channel')),
                    },
                )

            entry_label = 'Lead' if entry_kind == 'lead' else 'Intake'
            messages.success(request, f'{entry_label} cadastrado com sucesso na Central de Intake.')
            return redirect(self._get_quick_create_success_url(entry_kind))

        if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
            messages.error(request, 'Seu papel atual pode consultar a central, mas nao executar a fila por esta tela.')
            return redirect(self._get_success_url())

        form = IntakeQueueActionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A acao de entradas nao foi entendida. Revise a fila e tente novamente.')
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
            publish_manager_stream_event(
                event_type='intake.updated',
                meta={
                    'intake_id': result.intake_id,
                    'action': form.cleaned_data['action'],
                    'status': result.status,
                    'assigned_to_id': result.assigned_to_id,
                },
            )

        return redirect(self._get_success_url(form.cleaned_data.get('return_query', '')))


__all__ = ['IntakeCenterView']
