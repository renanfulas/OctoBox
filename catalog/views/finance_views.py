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

    def build_finance_filter_summary(self, filter_form):
        months_choices = dict(filter_form.fields['months'].choices)
        status_choices = dict(filter_form.fields['payment_status'].choices)
        method_choices = dict(filter_form.fields['payment_method'].choices)

        months_value = '6'
        selected_plan = None
        payment_status = ''
        payment_method = ''

        if filter_form.is_valid():
            months_value = str(filter_form.cleaned_data.get('months') or '6')
            selected_plan = filter_form.cleaned_data.get('plan')
            payment_status = filter_form.cleaned_data.get('payment_status') or ''
            payment_method = filter_form.cleaned_data.get('payment_method') or ''

        return [
            {
                'label': 'Janela atual',
                'value': months_choices.get(months_value, '6 meses'),
                'summary': 'Define o horizonte da leitura gerencial antes de comparar caixa e retenção.',
            },
            {
                'label': 'Plano em foco',
                'value': selected_plan.name if selected_plan else 'Todos os planos',
                'summary': 'Mostra se o recorte está amplo ou se já está olhando uma carteira específica.',
            },
            {
                'label': 'Status financeiro',
                'value': status_choices.get(payment_status, 'Todos'),
                'summary': 'Ajuda a separar leitura total de leitura de pressão operacional.',
            },
            {
                'label': 'Método de pagamento',
                'value': method_choices.get(payment_method, 'Todos'),
                'summary': 'Útil quando a análise precisa isolar comportamento de recebimento.',
            },
        ]

    def build_finance_workspace_context(self, snapshot):
        operational_queue = build_operational_queue_snapshot()
        filter_form = snapshot['filter_form']
        financial_alerts = snapshot['financial_alerts']
        plan_portfolio = snapshot['plan_portfolio']
        recent_movements = snapshot['recent_movements']
        finance_pulse = snapshot['finance_pulse']
        active_plans = sum(1 for plan in plan_portfolio if plan.active)
        inactive_plans = max(len(plan_portfolio) - active_plans, 0)
        top_plan = next(iter(plan_portfolio), None)
        top_plan_revenue = top_plan.revenue_this_month if top_plan else 0
        canceled_recent_movements = sum(1 for movement in recent_movements if movement.status == 'canceled')
        completed_recent_movements = sum(1 for movement in recent_movements if movement.status == 'active')
        pressure_total = len(operational_queue) + len(financial_alerts)
        if pressure_total > 0:
            priority_badge = 'warning'
            priority_label = f'{pressure_total} sinal(is) agora'
            priority_summary = 'Resolva régua e fila antes de gastar energia em tendência ou reposicionamento comercial.'
        else:
            priority_badge = 'success'
            priority_label = 'Pressão controlada'
            priority_summary = 'O recorte não mostra urgência operacional forte agora, então a leitura pode descer para estrutura com mais segurança.'

        finance_right_rail_snapshot = [
            {
                'label': 'Pressão combinada',
                'value': pressure_total,
                'summary': 'Soma contato assistido com fila financeira no recorte atual.',
            },
            {
                'label': 'Em aberto',
                'value': f"R$ {finance_pulse['open']:.2f}",
                'summary': 'Mostra o volume que ainda pede conversão em caixa.',
            },
            {
                'label': 'Alunos em atraso',
                'value': finance_pulse['overdue_students'],
                'summary': 'Ajuda a medir se a pressão é pontual ou já alcançou a base.',
            },
        ]
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
                'summary': f"Recebido: R$ {finance_pulse['received']:.2f} | Em aberto: R$ {finance_pulse['open']:.2f}.",
                'pill_class': 'accent',
                'href': '#finance-trend-board',
                'href_label': 'Ver tendência',
            },
        ]
        finance_command_cards = [
            {
                'label': 'Primeiro ajuste o recorte',
                'value': self.build_finance_filter_summary(filter_form)[0]['value'],
                'summary': 'Confirme janela, carteira e método antes de comparar número com número e concluir algo errado.',
                'href': '#finance-control-board',
                'href_label': 'Abrir recorte',
                'pill_class': 'info',
            },
            {
                'label': 'Depois resolva a pressão viva',
                'value': f'{len(operational_queue)} contato(s) e {len(financial_alerts)} alerta(s)',
                'summary': 'Régua e fila precisam vir antes de tendência, porque caixa ruim costuma começar como fila ignorada.',
                'href': '#finance-priority-board',
                'href_label': 'Abrir pressão atual',
                'pill_class': 'warning' if len(operational_queue) or len(financial_alerts) else 'success',
            },
            {
                'label': 'Feche com a estrutura comercial',
                'value': f'{active_plans} ativo(s) e {len(recent_movements)} movimento(s)',
                'summary': 'Só desça para portfólio, mix e movimentos depois que o recorte e a urgência operacional estiverem claros.',
                'href': '#finance-portfolio-board',
                'href_label': 'Abrir estrutura',
                'pill_class': 'accent',
            },
        ]
        finance_trend_guides = [
            {
                'label': 'Leia tendência assim',
                'value': 'Receita real antes de discurso',
                'summary': 'Se a curva sobe mas a régua continua pressionada, o caixa está entrando com atrito operacional escondido.',
            },
            {
                'label': 'Leia churn assim',
                'value': 'Crescimento com retenção',
                'summary': 'Ativação sem retenção não fortalece carteira; só aumenta sensação temporária de avanço.',
            },
            {
                'label': 'Decisão correta',
                'value': 'Fluxo antes de preço',
                'summary': 'Antes de mexer em oferta ou ticket, confirme se o ruído atual vem mesmo do produto e não da operação.',
            },
        ]
        finance_plan_creation_focus = [
            {
                'label': 'Comece pelo núcleo da oferta',
                'summary': 'Nome, valor e ciclo precisam continuar entendíveis para venda, matrícula e cobrança sem tradução oral.',
                'pill_class': 'accent',
            },
            {
                'label': 'Depois valide a entrega',
                'summary': 'A descrição comercial deve reduzir ambiguidade para recepção, manager e leitura futura da carteira.',
                'pill_class': 'info',
            },
            {
                'label': 'Feche com ativação consciente',
                'summary': 'Ativar um plano ruim ou vago só espalha ruído para a base inteira e empobrece a leitura comercial.',
                'pill_class': 'warning',
            },
        ]
        return {
            'page_title': 'Financeiro',
            'page_subtitle': 'Aqui o box ganha leitura comercial: planos, receita, retencao e sinais operacionais que depois conversam com a jornada do aluno.',
            'can_manage_finance': self.get_base_context()['current_role'].slug in (ROLE_OWNER, ROLE_MANAGER),
            'finance_filter_form': filter_form,
            'finance_metrics': snapshot['finance_metrics'],
            'finance_pulse': finance_pulse,
            'plan_portfolio': plan_portfolio,
            'plan_mix': snapshot['plan_mix'],
            'monthly_comparison': snapshot['monthly_comparison'],
            'comparison_peaks': snapshot['comparison_peaks'],
            'financial_alerts': financial_alerts,
            'recent_movements': recent_movements,
            'operational_queue': operational_queue,
            'operational_metrics': build_operational_queue_metrics(operational_queue),
            'finance_right_rail_snapshot': finance_right_rail_snapshot,
            'finance_right_rail_priority_badge': priority_badge,
            'finance_right_rail_priority_label': priority_label,
            'finance_right_rail_priority_summary': priority_summary,
            'finance_operational_focus': operational_focus,
            'finance_command_cards': finance_command_cards,
            'finance_structure_focus': [
                {
                    'label': 'Comece pela carteira de planos',
                    'summary': f'{active_plans} plano(s) ativo(s) e {inactive_plans} inativo(s) mostram se a vitrine comercial está limpa ou já acumulou ruído.',
                    'pill_class': 'accent',
                    'href': '#finance-portfolio-board',
                    'href_label': 'Ver carteira de planos',
                },
                {
                    'label': 'Depois veja a concentração do mix',
                    'summary': (
                        f'{top_plan.name} lidera a base com {top_plan.active_enrollments} matrícula(s) ativa(s), então vale medir dependência antes de mexer em preço.'
                        if top_plan else
                        'Sem plano dominante ainda. O mix continua aberto para leitura e composição comercial.'
                    ),
                    'pill_class': 'info',
                    'href': '#finance-mix-board',
                    'href_label': 'Ver mix comercial',
                },
                {
                    'label': 'Feche com a movimentação recente',
                    'summary': f'{len(recent_movements)} movimento(s) recente(s) e {canceled_recent_movements} cancelamento(s) ajudam a separar ajuste pontual de mudança estrutural na carteira.',
                    'pill_class': 'warning' if canceled_recent_movements > 0 else 'success',
                    'href': '#finance-movements-board',
                    'href_label': 'Ver movimentos recentes',
                },
            ],
            'finance_trend_guides': finance_trend_guides,
            'finance_plan_creation_focus': finance_plan_creation_focus,
            'finance_plan_creation_guardrails': [
                'Plano bom precisa nascer claro para vender, cobrar e sustentar carteira sem explicação paralela.',
                'Se nome, valor e entrega não conversarem entre si, o problema vai aparecer depois como ruído comercial e financeiro.',
                'Ativação deve ser decisão consciente; plano vago ativo contamina leitura de portfólio e mix.',
            ],
            'finance_portfolio_guides': [
                {
                    'label': 'Carteira ativa',
                    'value': f'{active_plans} plano(s)',
                    'summary': 'Produtos que ainda sustentam venda, recorrência e leitura de preço.',
                },
                {
                    'label': 'Carteira inativa',
                    'value': f'{inactive_plans} plano(s)',
                    'summary': 'Itens que podem estar ocupando espaço visual sem utilidade comercial real.',
                },
                {
                    'label': 'Plano que mais pesa',
                    'value': top_plan.name if top_plan else 'Sem plano dominante',
                    'summary': (
                        f'Recebeu R$ {top_plan_revenue:.2f} no mês e merece leitura antes de qualquer ajuste comercial.'
                        if top_plan else
                        'A carteira ainda está dispersa, então o mix precisa ser lido antes de mexer em preço.'
                    ),
                },
            ],
            'finance_mix_guides': [
                'Veja primeiro qual plano concentra a base ativa para evitar decisões de preço baseadas em sensação.',
                'Compare concentração, receita recebida e aberto financeiro antes de chamar um problema de ticket.',
                'Se o mix parecer saudável, valide os movimentos recentes antes de concluir que houve mudança estrutural.',
            ],
            'finance_movement_guides': [
                {
                    'label': 'Movimentos ativos',
                    'value': completed_recent_movements,
                    'summary': 'Indicam entrada ou permanência recente na carteira.',
                },
                {
                    'label': 'Cancelamentos no recorte',
                    'value': canceled_recent_movements,
                    'summary': 'Mostram pressão real sobre retenção e composição da base.',
                },
                {
                    'label': 'Leitura correta',
                    'value': 'Mudança estrutural',
                    'summary': 'Só conclua isso quando cancelamentos e redistribuição de mix aparecerem juntos.',
                },
            ],
            'finance_filter_summary': self.build_finance_filter_summary(filter_form),
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
        context['plan_form_focus'] = [
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
        context['plan_form_guardrails'] = [
            'Plano bom precisa ser claro para vender, cobrar e explicar sem traducao improvisada.',
            'Valor e ciclo devem parecer consistentes com a entrega prometida e com o tipo de aluno que a carteira quer reter.',
            'Se a descricao ficar vaga, a recepcao e o financeiro acabam preenchendo a lacuna no improviso.',
        ]
        context['plan_form_summary_cards'] = [
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
        ]
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
