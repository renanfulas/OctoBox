"""
ARQUIVO: views da area financeira do catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP de financeiro, exportacoes, planos e comunicacao no app catalog.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from catalog.finance_communication_http import handle_finance_communication_view_post
from catalog.finance_center_context import build_finance_center_view_context
from catalog.finance_plan_actions import create_membership_plan_from_finance_center
from catalog.finance_queries import build_finance_snapshot
from catalog.forms import MembershipPlanQuickForm
from catalog.presentation import build_finance_center_page, build_membership_plan_page
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.services.membership_plan_workflows import (
    run_membership_plan_update_workflow,
)
from finance.models import MembershipPlan
from reporting.application.catalog_reports import build_finance_report
from reporting.facade import run_report_response_build
from shared_support.security import check_export_quota

from .catalog_base_views import CatalogBaseView


class FinanceWorkspaceContextMixin:
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)
    finance_filter_keys = ('months', 'plan', 'payment_status', 'payment_method', 'queue_focus')
    finance_filter_session_key = 'finance_center_last_filter_state_v1'

    def _build_filter_querydict(self, values):
        params = QueryDict('', mutable=True)
        for key in self.finance_filter_keys:
            params[key] = values.get(key, '')
        return params

    def get_effective_finance_filter_params(self):
        if self.request.GET.get('reset_filters') == '1':
            self.request.session.pop(self.finance_filter_session_key, None)
            return QueryDict('', mutable=True), False, False

        has_explicit_filters = any(key in self.request.GET for key in self.finance_filter_keys)
        if has_explicit_filters:
            stored_values = {key: self.request.GET.get(key, '') for key in self.finance_filter_keys}
            self.request.session[self.finance_filter_session_key] = stored_values
            return self._build_filter_querydict(stored_values), True, False

        stored_values = self.request.session.get(self.finance_filter_session_key)
        if stored_values:
            return self._build_filter_querydict(stored_values), False, True

        return QueryDict('', mutable=True), False, False

    def get_finance_export_links(self, params=None):
        encoded_params = (params or self.request.GET).urlencode()
        return {
            'csv': f"{reverse('finance-report-export', args=['csv'])}?{encoded_params}" if encoded_params else reverse('finance-report-export', args=['csv']),
            'pdf': f"{reverse('finance-report-export', args=['pdf'])}?{encoded_params}" if encoded_params else reverse('finance-report-export', args=['pdf']),
        }


class FinanceCenterView(FinanceWorkspaceContextMixin, CatalogBaseView, FormView):
    template_name = 'catalog/finance.html'
    form_class = MembershipPlanQuickForm

    def get_success_url(self):
        return reverse('finance-center')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return build_finance_center_view_context(
            self,
            context=context,
            form=kwargs.get('form') or self.get_form(),
        )

    def form_valid(self, form):
        result = create_membership_plan_from_finance_center(
            actor=self.request.user,
            current_role=self.get_base_context()['current_role'],
            form=form,
        )
        if not result['ok']:
            messages.error(self.request, 'Seu papel atual pode consultar o financeiro, mas nao criar planos por esta tela.')
            return redirect(self.get_success_url())

        plan = result['plan']
        messages.success(self.request, f'Plano {plan.name} cadastrado com sucesso.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'O plano nao foi salvo. Revise os campos destacados.')
        return super().form_invalid(form)


class FinanceReportExportView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)

    def get(self, request, report_format, *args, **kwargs):
        allowed, count = check_export_quota(user_id=request.user.id, scope=f'finance-report-{report_format}')
        if not allowed:
            messages.warning(request, 'Cota de exportacao semanal atingida para este relatorio financeiro. O OctoBox reserva o motor para operacoes criticas, limitando exportacoes pesadas a 2 por semana.')
            return redirect('finance-center')

        snapshot = build_finance_snapshot(request.GET)
        try:
            return run_report_response_build(build_finance_report(snapshot=snapshot, report_format=report_format))
        except ValueError as exc:
            raise Http404(str(exc)) from exc


class FinanceCommunicationActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def post(self, request, *args, **kwargs):
        return handle_finance_communication_view_post(request=request)


class MembershipPlanQuickUpdateView(CatalogBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)
    template_name = 'catalog/finance-plan-form.html'
    form_class = MembershipPlanQuickForm
    object = None

    def get_success_url(self):
        return reverse('finance-center')

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(MembershipPlan, pk=kwargs['plan_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        page_payload = build_membership_plan_page(
            form=context.get('form'),
            plan=self.object,
            current_role_slug=context['current_role'].slug,
        )
        return attach_catalog_page_payload(
            context,
            payload_key='finance_plan_page',
            payload=page_payload,
            include_sections=('context', 'shell'),
        )

    def form_valid(self, form):
        plan = run_membership_plan_update_workflow(
            actor=self.request.user,
            form=form,
            changed_fields=list(form.changed_data),
        )
        messages.success(self.request, f'Plano {plan.name} atualizado com sucesso.')
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, 'O plano nao foi salvo. Revise os campos destacados.')
        return super().form_invalid(form)
