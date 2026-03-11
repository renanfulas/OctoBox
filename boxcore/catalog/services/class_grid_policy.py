"""
ARQUIVO: policy operacional da grade de aulas.

POR QUE ELE EXISTE:
- concentra as regras de editabilidade e exclusao de aulas para evitar logica espalhada entre form, view e service.

O QUE ESTE ARQUIVO FAZ:
1. monta a policy aplicavel a uma aula.
2. define quais status a edicao rapida pode usar.
3. valida cenarios de reabertura e exclusao com historico vinculado.

PONTOS CRITICOS:
- essa policy governa mutacoes da agenda real e precisa refletir a regra operacional correta.
"""

from dataclasses import dataclass

from boxcore.models import SessionStatus

from . import class_grid_messages as grid_messages


@dataclass(frozen=True)
class ClassGridSessionPolicy:
    quick_edit_status_choices: tuple[tuple[str, str], ...]
    initial_quick_edit_status: str
    can_delete: bool
    delete_error_message: str = ''

    def validate_quick_edit_status(self, new_status):
        if self.initial_quick_edit_status == SessionStatus.COMPLETED and new_status != SessionStatus.CANCELED:
            raise ValueError(grid_messages.COMPLETED_SESSION_REOPEN_BLOCKED)

    def ensure_can_delete(self):
        if not self.can_delete:
            raise ValueError(self.delete_error_message)


def build_class_grid_session_policy(session):
    delete_error_message = ''
    can_delete = not session.attendances.exists()
    if not can_delete:
        delete_error_message = grid_messages.SESSION_DELETE_WITH_ATTENDANCE_BLOCKED

    return ClassGridSessionPolicy(
        quick_edit_status_choices=(
            (SessionStatus.SCHEDULED, 'Agendada'),
            (SessionStatus.CANCELED, 'Cancelada'),
        ),
        initial_quick_edit_status=session.status,
        can_delete=can_delete,
        delete_error_message=delete_error_message,
    )