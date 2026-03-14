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
from access.shell_actions import build_shell_action_buttons
from catalog.finance_queries import build_finance_snapshot
from catalog.forms import MembershipPlanQuickForm
from catalog.presentation import build_finance_center_page
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
from shared_support.page_payloads import attach_page_payload, build_page_payload

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
        snapshot = self.get_finance_snapshot()
        operational_queue = build_operational_queue_snapshot()
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
        plan_form_focus = [
            {
                'label': 'Comece pelo coracao da oferta',
                'summary': 'Nome, valor e ciclo precisam continuar legiveis para venda, cobranca e carteira sem depender de explicacao oral.',
                'pill_class': 'accent',
                'href': '#plan-form-core',
                'href_label': 'Editar nucleo',
            },
            {
                'label': 'Depois valide a entrega',
                'summary': 'A descricao comercial deve reduzir ambiguidade para recepcao, manager e leitura futura do proprio plano.',
                'pill_class': 'info',
                'href': '#plan-form-delivery',
                'href_label': 'Revisar entrega',
            },
            {
                'label': 'Feche com impacto na carteira',
                'summary': 'Status, ritmo semanal e leitura rapida precisam deixar claro se o plano fortalece a carteira ou so ocupa espaco visual.',
                'pill_class': 'warning' if self.object.active else 'info',
                'href': '#plan-form-summary',
                'href_label': 'Ler impacto',
            },
        ]
        page_payload = build_page_payload(
            context={
                'page_key': 'finance-plan-form',
                'title': 'Editar plano',
                'subtitle': 'Ajuste valor, ciclo e proposta comercial sem sair do centro financeiro.',
            },
            shell={
                'shell_action_buttons': build_shell_action_buttons(
                    priority=plan_form_focus[0],
                    pending=plan_form_focus[1],
                    next_action=plan_form_focus[2],
                    scope='finance-plan-form',
                ),
            },
            data={
                'form': context.get('form'),
                'plan_object': self.object,
                'plan_form_guardrails': [
                    'Plano bom precisa ser claro para vender, cobrar e explicar sem traducao improvisada.',
                    'Valor e ciclo devem parecer consistentes com a entrega prometida e com o tipo de aluno que a carteira quer reter.',
                    'Se a descricao ficar vaga, a recepcao e o financeiro acabam preenchendo a lacuna no improviso.',
                ],
                'plan_form_summary_cards': [
                    {
                        'label': 'Status comercial',
                        'value': 'Ativo' if self.object.active else 'Inativo',
                        'summary': 'Mostra se o plano segue disponivel para compor carteira e novas vendas.',
                    },
                    {
                        'label': 'Ritmo semanal',
                        'value': f'{self.object.sessions_per_week} aula(s)',
                        'summary': 'Ajuda a ler se a proposta cabe como entrada, meio de carteira ou oferta premium.',
                    },
                    {
                        'label': 'Entrega comercial',
                        'value': 'Descrita' if self.object.description else 'Pede texto',
                        'summary': 'Evita que a equipe dependa de memoria oral para explicar o plano.',
                    },
                ],
            },
        )
        attach_page_payload(
            context,
            payload_key='finance_plan_page',
            payload=page_payload,
            include_sections=('context', 'shell'),
        )
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
