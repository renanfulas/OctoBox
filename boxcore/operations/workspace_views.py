"""
ARQUIVO: views de workspace operacional por papel.

POR QUE ELE EXISTE:
- Separa a camada HTTP das areas de Owner, DEV, Manager e Coach.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza as areas operacionais por papel com snapshots prontos.
2. Mantem as views focadas em permissao, contexto e template.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta a experiencia operacional por papel.
"""

from boxcore.access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER

from .base_views import OperationBaseView
from .workspace_snapshot_queries import (
    build_coach_workspace_snapshot,
    build_dev_workspace_snapshot,
    build_manager_workspace_snapshot,
    build_owner_workspace_snapshot,
)


class OwnerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER,)
    template_name = 'operations/owner.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context.update(build_owner_workspace_snapshot(today=context['today']))
        return context


class DevWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_DEV,)
    template_name = 'operations/dev.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context.update(build_dev_workspace_snapshot())
        return context


class ManagerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_MANAGER,)
    template_name = 'operations/manager.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context.update(build_manager_workspace_snapshot())
        return context


class CoachWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_COACH,)
    template_name = 'operations/coach.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context.update(build_coach_workspace_snapshot(today=context['today']))
        return context