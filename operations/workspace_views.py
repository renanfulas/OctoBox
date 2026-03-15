"""
ARQUIVO: views de workspace operacional por papel.

POR QUE ELE EXISTE:
- publica as telas de owner, dev, manager e coach no app operations.

O QUE ESTE ARQUIVO FAZ:
1. renderiza workspaces por papel.
2. consome snapshots prontos da camada de queries.

PONTOS CRITICOS:
- qualquer regressao aqui afeta a experiencia operacional por papel.
"""

from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from shared_support.page_payloads import attach_page_payload

from operations.facade import (
    build_coach_workspace_snapshot,
    build_dev_workspace_snapshot,
    build_manager_workspace_snapshot,
    build_owner_workspace_snapshot,
    build_reception_workspace_snapshot,
    build_reception_preview_workspace_snapshot,
)
from operations.presentation import build_operation_workspace_page

from .base_views import OperationBaseView


class OwnerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER,)
    template_name = 'operations/owner.html'
    page_title = 'Minha operação'
    page_subtitle = 'Crescimento, caixa e estrutura sem leitura longa.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_owner_workspace_snapshot(today=context['today'])
        payload = build_operation_workspace_page(
            page_key='operations-owner',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-owner',
            snapshot=snapshot,
            current_role_slug=context['current_role'].slug,
            focus_key='owner_operational_focus',
        )
        attach_page_payload(context, payload_key='operation_page', payload=payload)
        return context


class DevWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_DEV,)
    template_name = 'operations/dev.html'
    page_title = 'Minha operação'
    page_subtitle = 'Rastros, fronteiras e manutencao sem invadir a operacao.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_dev_workspace_snapshot()
        payload = build_operation_workspace_page(
            page_key='operations-dev',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-owner',
            snapshot=snapshot,
            current_role_slug=context['current_role'].slug,
            focus_key='dev_operational_focus',
        )
        attach_page_payload(context, payload_key='operation_page', payload=payload)
        return context


class ManagerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_MANAGER,)
    template_name = 'operations/manager.html'
    page_title = 'Minha operação'
    page_subtitle = 'Triagem, vinculo e cobranca em ordem curta.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_manager_workspace_snapshot()
        payload = build_operation_workspace_page(
            page_key='operations-manager',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-manager',
            snapshot=snapshot,
            current_role_slug=context['current_role'].slug,
            focus_key='manager_operational_focus',
        )
        attach_page_payload(context, payload_key='operation_page', payload=payload)
        return context


class CoachWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_COACH,)
    template_name = 'operations/coach.html'
    page_title = 'Minha operação'
    page_subtitle = 'Aula, presenca e ocorrencia com leitura curta.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_coach_workspace_snapshot(today=context['today'])
        payload = build_operation_workspace_page(
            page_key='operations-coach',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-coach',
            snapshot=snapshot,
            current_role_slug=context['current_role'].slug,
            focus_key='coach_operational_focus',
        )
        attach_page_payload(context, payload_key='operation_page', payload=payload)
        return context


class ReceptionPreviewWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV)
    template_name = 'operations/reception_preview.html'
    page_title = 'Recepcao em preparo'
    page_subtitle = 'Balcao, grade e cobranca curta antes do rollout.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_reception_preview_workspace_snapshot(today=context['today'])
        payload = build_operation_workspace_page(
            page_key='operations-reception-preview',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-reception-preview',
            snapshot=snapshot,
            current_role_slug=context['current_role'].slug,
            focus_key='reception_preview_focus',
            capabilities={'can_manage_reception_preview_payments': context['current_role'].slug == ROLE_OWNER},
        )
        attach_page_payload(context, payload_key='operation_page', payload=payload)
        return context


class ReceptionWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_RECEPTION)
    template_name = 'operations/reception.html'
    page_title = 'Minha operação'
    page_subtitle = 'Chegada, agenda e cobranca curta no balcao.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        snapshot = build_reception_workspace_snapshot(today=context['today'])
        payload = build_operation_workspace_page(
            page_key='operations-reception',
            title=self.page_title,
            subtitle=self.page_subtitle,
            scope='operations-reception',
            snapshot=snapshot,
            current_role_slug=context['current_role'].slug,
            focus_key='reception_focus',
            capabilities={'can_manage_reception_payments': context['current_role'].slug in (ROLE_OWNER, ROLE_RECEPTION)},
        )
        attach_page_payload(context, payload_key='operation_page', payload=payload)
        return context
