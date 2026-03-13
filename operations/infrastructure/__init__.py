"""
ARQUIVO: adapters Django das operacoes de aulas.

POR QUE ELE EXISTE:
- centraliza o ponto de entrada concreto da grade fora do catalogo historico.

O QUE ESTE ARQUIVO FAZ:
1. expoe execucoes concretas da grade de aulas.
2. reexporta limites de agenda para compatibilidade.

PONTOS CRITICOS:
- as views e fachadas devem depender deste pacote, nao da implementacao interna dos adapters.
"""

from .django_class_grid_audit import DjangoClassGridAudit
from .django_class_grid_clock import DjangoClassGridClockPort
from .django_class_grid_coaches import DjangoClassGridCoachResolver
from .django_class_grid_sessions import DjangoClassGridSessionStore
from .django_workspace_store import DjangoWorkspaceStore
from .django_class_grid import (
    execute_create_class_schedule_command,
    execute_delete_class_session_command,
    execute_update_class_session_command,
)
from .django_schedule_limits import (
    DAILY_SESSION_LIMIT,
    MONTHLY_SESSION_LIMIT,
    WEEKLY_SESSION_LIMIT,
    ensure_schedule_limits,
    get_month_bounds,
    get_week_bounds,
)
from .django_clock import DjangoWorkspaceClockPort
from .django_workspace_actions import (
    execute_apply_attendance_action_command,
    execute_create_technical_behavior_note_command,
    execute_link_payment_enrollment_command,
)

__all__ = [
    'DAILY_SESSION_LIMIT',
    'DjangoClassGridAudit',
    'DjangoClassGridClockPort',
    'DjangoClassGridCoachResolver',
    'DjangoClassGridSessionStore',
    'DjangoWorkspaceStore',
    'DjangoWorkspaceClockPort',
    'MONTHLY_SESSION_LIMIT',
    'WEEKLY_SESSION_LIMIT',
    'execute_apply_attendance_action_command',
    'ensure_schedule_limits',
    'execute_create_class_schedule_command',
    'execute_create_technical_behavior_note_command',
    'execute_delete_class_session_command',
    'execute_link_payment_enrollment_command',
    'execute_update_class_session_command',
    'get_month_bounds',
    'get_week_bounds',
]