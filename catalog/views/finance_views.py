"""
ARQUIVO: views da area financeira do catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP de financeiro, exportacoes, planos e comunicacao no app catalog.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from auditing import log_audit_event
from auditing.models import AuditEvent
from catalog.finance_queries import build_finance_snapshot
from catalog.forms import FinanceCommunicationActionForm, MembershipPlanQuickForm
from catalog.presentation import build_finance_center_page, build_membership_plan_page
from catalog.presentation.shared import attach_catalog_page_payload
from catalog.services.finance_communication_actions import handle_finance_communication_action
from catalog.services.membership_plan_workflows import (
    run_membership_plan_create_workflow,
    run_membership_plan_update_workflow,
)
from catalog.services.operational_queue import build_operational_queue_snapshot
from finance.models import MembershipPlan, Payment
from reporting.application.catalog_reports import build_finance_report
from reporting.facade import run_report_response_build
from shared_support.cascade.contracts import build_cascade_intent, merge_cascade_metadata
from shared_support.cascade.ownership import resolve_actor_box_id, resolve_box_owner_user_id
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.operational_contact_memory import (
    CONTACT_COOLDOWN_DAYS,
    CONTACT_OWNERSHIP_MANAGER_OWNER,
    CONTACT_STAGE_FIRST_TOUCH_OPENED,
    CONTACT_STAGE_FOLLOW_UP_ACTIVE,
    CONTACT_STAGE_UNREACHED,
    FINANCE_CONTACT_ACTIONS,
    MANAGER_FINANCE_WHATSAPP_ACTION,
    OWNER_FINANCE_WHATSAPP_ACTION,
    RECEPTION_FINANCE_WHATSAPP_ACTION,
    build_contact_memory_metadata,
)
from shared_support.operational_settings import get_operational_whatsapp_repeat_block_hours
from shared_support.security import check_export_quota
from shared_support.student_event_stream import publish_student_stream_event

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
        base_context = self.get_base_context()
        context.update(base_context)
        operational_queue = build_operational_queue_snapshot()
        effective_params, filters_applied_now, filters_restored = self.get_effective_finance_filter_params()
        default_panel_override = 'tab-finance-filters' if (filters_applied_now or self.request.GET.get('reset_filters') == '1') else None
        snapshot = build_finance_snapshot(effective_params, operational_queue=operational_queue, persist_follow_ups=True)
        page_payload = build_finance_center_page(
            snapshot=snapshot,
            operational_queue=operational_queue,
            export_links=self.get_finance_export_links(effective_params),
            current_role_slug=base_context['current_role'].slug,
            form=kwargs.get('form') or self.get_form(),
            default_panel_override=default_panel_override,
            filter_state_restored=filters_restored,
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
            return run_report_response_build(build_finance_report(snapshot=snapshot, report_format=report_format))
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

        payment_id = form.cleaned_data.get('payment_id')
        prior_touch_exists = False
        if payment_id:
            prior_touch_exists = AuditEvent.objects.filter(
                action__in=FINANCE_CONTACT_ACTIONS,
                target_model='payment',
                target_id=str(payment_id),
            ).exists()

        role_action_map = {
            ROLE_MANAGER: MANAGER_FINANCE_WHATSAPP_ACTION,
            ROLE_RECEPTION: RECEPTION_FINANCE_WHATSAPP_ACTION,
            ROLE_OWNER: OWNER_FINANCE_WHATSAPP_ACTION,
        }
        current_role = get_user_role(request.user)
        current_role_slug = getattr(current_role, 'slug', '')
        action_name = role_action_map.get(current_role_slug, MANAGER_FINANCE_WHATSAPP_ACTION)
        stage_before = CONTACT_STAGE_UNREACHED if not prior_touch_exists else CONTACT_STAGE_FOLLOW_UP_ACTIVE
        stage_after = CONTACT_STAGE_FIRST_TOUCH_OPENED if not prior_touch_exists else CONTACT_STAGE_FOLLOW_UP_ACTIVE
        cooldown_until = (timezone.now() + timedelta(days=CONTACT_COOLDOWN_DAYS)).isoformat()
        payment = Payment.objects.filter(pk=payment_id).first() if payment_id else None
        enrollment_id = form.cleaned_data.get('enrollment_id')
        audit_target = payment or result['student']
        box_id = resolve_actor_box_id(request.user)
        cascade_intent = build_cascade_intent(
            box_id=box_id,
            owner_user_id=resolve_box_owner_user_id(box_id),
            requested_by_user_id=request.user.id,
            requested_by_role=current_role_slug or ROLE_MANAGER,
            subject_type='payment' if payment_id else 'student',
            subject_id=payment_id or result['student'].id,
            action_kind=f'finance_{form.cleaned_data["action_kind"]}_whatsapp',
            channel='whatsapp',
            surface=current_role_slug or 'finance',
        )

        log_audit_event(
            actor=request.user,
            action=action_name,
            target=audit_target,
            description=f'Contato de cobranca aberto por WhatsApp para {result["student"].full_name}.',
            metadata=merge_cascade_metadata(
                build_contact_memory_metadata(
                    board_key='finance',
                    channel='whatsapp',
                    subject_type='payment' if payment_id else 'student',
                    subject_id=payment_id or result['student'].id,
                    subject_label=result['student'].full_name,
                    student_id=result['student'].id,
                    payment_id=payment_id,
                    intake_id=None,
                    stage_before=stage_before,
                    stage_after=stage_after,
                    ownership_scope=CONTACT_OWNERSHIP_MANAGER_OWNER,
                    cooldown_until=cooldown_until,
                    is_first_touch=not prior_touch_exists,
                ),
                intent=cascade_intent,
            ),
        )
        publish_manager_stream_event(
            event_type='student.payment.updated',
            meta={
                'student_id': result['student'].id,
                'payment_id': payment_id,
                'enrollment_id': enrollment_id,
                'action': action_name,
            },
        )
        publish_student_stream_event(
            student_id=result['student'].id,
            event_type='student.payment.updated',
            meta={
                'payment_id': payment_id,
                'action': action_name,
            },
        )

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
