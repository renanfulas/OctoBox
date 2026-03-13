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
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER
from catalog.finance_queries import build_finance_snapshot
from catalog.forms import MembershipPlanQuickForm
from catalog.services.finance_communication_actions import handle_finance_communication_action
from catalog.services.membership_plan_workflows import (
    run_membership_plan_create_workflow,
    run_membership_plan_update_workflow,
)
from catalog.services.operational_queue import build_operational_queue_metrics, build_operational_queue_snapshot
from finance.models import MembershipPlan
from reporting.application.catalog_reports import build_finance_report
from reporting.infrastructure import build_report_response

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

    def build_finance_workspace_context(self, snapshot):
        operational_queue = build_operational_queue_snapshot()
        financial_alerts = snapshot['financial_alerts']
        operational_focus = [
            {
                'label': 'Cobrança pede contato',
                'summary': f'{len(operational_queue)} caso(s) já têm abordagem sugerida e não deveriam esperar outra leitura para virar ação.',
                'pill_class': 'warning' if len(operational_queue) > 0 else 'success',
                'href': '#finance-rail-board',
                'href_label': 'Abrir régua',
            },
            {
                'label': 'Fila pressionando caixa',
                'summary': f'{len(financial_alerts)} cobrança(s) já aparecem como pendência ou atraso no recorte atual.',
                'pill_class': 'warning' if len(financial_alerts) > 0 else 'info',
                'href': '#finance-queue-board',
                'href_label': 'Ver fila financeira',
            },
            {
                'label': 'Pulso executivo',
                'summary': f"Recebido: R$ {snapshot['finance_pulse']['received']:.2f} | Em aberto: R$ {snapshot['finance_pulse']['open']:.2f}.",
                'pill_class': 'accent',
                'href': '#finance-trend-board',
                'href_label': 'Ver tendência',
            },
        ]
        return {
            'page_title': 'Financeiro',
            'page_subtitle': 'Aqui o box ganha leitura comercial: planos, receita, retencao e sinais operacionais que depois conversam com a jornada do aluno.',
            'can_manage_finance': self.get_base_context()['current_role'].slug in (ROLE_OWNER, ROLE_MANAGER),
            'finance_filter_form': snapshot['filter_form'],
            'finance_metrics': snapshot['finance_metrics'],
            'finance_pulse': snapshot['finance_pulse'],
            'plan_portfolio': snapshot['plan_portfolio'],
            'plan_mix': snapshot['plan_mix'],
            'monthly_comparison': snapshot['monthly_comparison'],
            'comparison_peaks': snapshot['comparison_peaks'],
            'financial_alerts': financial_alerts,
            'recent_movements': snapshot['recent_movements'],
            'operational_queue': operational_queue,
            'operational_metrics': build_operational_queue_metrics(operational_queue),
            'finance_operational_focus': operational_focus,
            'finance_export_links': self.get_finance_export_links(),
        }


class FinanceCenterView(FinanceWorkspaceContextMixin, CatalogBaseView, FormView):
    template_name = 'catalog/finance.html'
    form_class = MembershipPlanQuickForm

    def get_success_url(self):
        return reverse('finance-center')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context.update(self.build_finance_workspace_context(self.get_finance_snapshot()))
        return context

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
        snapshot = build_finance_snapshot(request.GET)
        try:
            return build_report_response(build_finance_report(snapshot=snapshot, report_format=report_format))
        except ValueError as exc:
            raise Http404(str(exc)) from exc


class FinanceCommunicationActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        result = handle_finance_communication_action(actor=request.user, payload=request.POST)
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
        context['page_title'] = 'Editar plano'
        context['page_subtitle'] = 'Ajuste valor, ciclo e proposta comercial sem sair do centro financeiro.'
        context['plan_object'] = self.object
        return context

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
