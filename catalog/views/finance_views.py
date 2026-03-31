"""
ARQUIVO: views da area financeira do catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP de financeiro, exportacoes, planos e comunicacao no app catalog.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from catalog.finance_queries import build_finance_snapshot
from catalog.forms import FinanceCommunicationActionForm, MembershipPlanQuickForm
from catalog.presentation import build_finance_center_page, build_membership_plan_page
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.services.finance_communication_actions import handle_finance_communication_action
from catalog.services.membership_plan_workflows import (
    run_membership_plan_create_workflow,
    run_membership_plan_update_workflow,
)
from catalog.services.operational_queue import build_operational_queue_metrics, build_operational_queue_snapshot
from finance.models import MembershipPlan
from reporting.application.catalog_reports import build_finance_report
from reporting.infrastructure import build_report_response
from shared_support.operational_settings import get_operational_whatsapp_repeat_block_hours
from shared_support.security import check_export_quota

from .catalog_base_views import CatalogBaseView


class FinanceWorkspaceContextMixin:
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)

    def get_finance_snapshot(self):
        return build_finance_snapshot(self.request.GET)

    def get_finance_export_links(self):
        return {
            'csv': f"{reverse('finance-report-export', args=['csv'])}?{self.request.GET.urlencode()}",
            'pdf': f"{reverse('finance-report-export', args=['pdf'])}?{self.request.GET.urlencode()}",
        }


class FinanceCenterView(FinanceWorkspaceContextMixin, CatalogBaseView, FormView):
    template_name = 'catalog/finance.html'
    form_class = MembershipPlanQuickForm

    def get_success_url(self):
        return reverse('finance-center')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_context = self.get_base_context()
        context.update(base_context)
        operational_queue = build_operational_queue_snapshot()
        snapshot = build_finance_snapshot(self.request.GET, operational_queue=operational_queue)
        page_payload = build_finance_center_page(
            snapshot=snapshot,
            operational_queue=operational_queue,
            operational_metrics=build_operational_queue_metrics(operational_queue),
            export_links=self.get_finance_export_links(),
            current_role_slug=base_context['current_role'].slug,
            form=kwargs.get('form') or self.get_form(),
        )
        return attach_catalog_page_payload(
            context,
            payload_key='finance_center_page',
            payload=page_payload,
            include_sections=('context', 'shell'),
        )

    def form_valid(self, form):
        current_role = self.get_base_context()['current_role']
        if current_role.slug not in (ROLE_OWNER, ROLE_MANAGER):
            messages.error(self.request, 'Seu papel atual pode consultar o financeiro, mas nao criar planos por esta tela.')
            return redirect(self.get_success_url())

        plan = run_membership_plan_create_workflow(actor=self.request.user, form=form)
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
            return build_report_response(build_finance_report(snapshot=snapshot, report_format=report_format))
        except ValueError as exc:
            raise Http404(str(exc)) from exc


class FinanceCommunicationActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION)

    def post(self, request, *args, **kwargs):
        open_in_whatsapp = request.POST.get('open_in_whatsapp') == '1'
        form = FinanceCommunicationActionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A acao de comunicacao nao foi registrada. Revise os dados do contato operacional.')
            return redirect('finance-center')

        result = handle_finance_communication_action(
            actor=request.user,
            action_kind=form.cleaned_data['action_kind'],
            student_id=form.cleaned_data['student_id'],
            payment_id=form.cleaned_data.get('payment_id'),
            enrollment_id=form.cleaned_data.get('enrollment_id'),
        )
        if result['blocked']:
            repeat_block_hours = get_operational_whatsapp_repeat_block_hours()
            if repeat_block_hours:
                messages.warning(request, f'Contato de WhatsApp ja registrado nas ultimas {repeat_block_hours}h para {result["student"].full_name}. Aguarde a proxima janela antes de repetir a mesma acao.')
            else:
                messages.warning(request, f'Contato de WhatsApp repetido bloqueado para {result["student"].full_name}.')
            return redirect('finance-center')

        if open_in_whatsapp and result['whatsapp_href']:
            return redirect(result['whatsapp_href'])

        messages.success(request, f'Contato operacional registrado para {result["student"].full_name}.')
        return redirect('finance-center')


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
