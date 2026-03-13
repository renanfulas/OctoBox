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

from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER

from operations.facade import (
    build_coach_workspace_snapshot,
    build_dev_workspace_snapshot,
    build_manager_workspace_snapshot,
    build_owner_workspace_snapshot,
)

from .base_views import OperationBaseView


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
