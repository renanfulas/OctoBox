"""
ARQUIVO: regras puras de editabilidade e exclusao da grade de aulas.

POR QUE ELE EXISTE:
- Remove da policy operacional a dependencia de model e relacionamento ORM so para decidir status e exclusao.

O QUE ESTE ARQUIVO FAZ:
1. Define a policy pura de edicao rapida da aula.
2. Decide se a exclusao pode acontecer com base em sinais primitivos.
3. Mantem as mensagens operacionais consistentes fora do adapter Django.

PONTOS CRITICOS:
- Esta camada deve permanecer pura; consultas de presenca e carregamento do model ficam em infrastructure ou forms.
"""

from dataclasses import dataclass

from operations.application import class_grid_messages as grid_messages


SCHEDULED_STATUS = 'scheduled'
CANCELED_STATUS = 'canceled'
COMPLETED_STATUS = 'completed'

STATUS_LABELS = {
    SCHEDULED_STATUS: 'Agendada',
    CANCELED_STATUS: 'Cancelada',
    COMPLETED_STATUS: 'Concluída',
    'open': 'Liberada',
}


@dataclass(frozen=True, slots=True)
class ClassGridSessionPolicy:
    quick_edit_status_choices: tuple[tuple[str, str], ...]
    initial_quick_edit_status: str
    can_delete: bool
    delete_error_message: str = ''

    def validate_quick_edit_status(self, new_status):
        if self.initial_quick_edit_status == COMPLETED_STATUS and new_status not in (COMPLETED_STATUS, CANCELED_STATUS):
            raise ValueError(grid_messages.COMPLETED_SESSION_REOPEN_BLOCKED)

    def ensure_can_delete(self):
        if not self.can_delete:
            raise ValueError(self.delete_error_message)


def build_class_grid_session_policy(*, initial_status: str, has_attendance: bool) -> ClassGridSessionPolicy:
    delete_error_message = ''
    can_delete = not has_attendance
    if not can_delete:
        delete_error_message = grid_messages.SESSION_DELETE_WITH_ATTENDANCE_BLOCKED

    quick_edit_status_choices = [
        (SCHEDULED_STATUS, STATUS_LABELS[SCHEDULED_STATUS]),
        (CANCELED_STATUS, STATUS_LABELS[CANCELED_STATUS]),
    ]
    if initial_status and initial_status not in {SCHEDULED_STATUS, CANCELED_STATUS}:
        quick_edit_status_choices.insert(0, (initial_status, STATUS_LABELS.get(initial_status, initial_status)))

    return ClassGridSessionPolicy(
        quick_edit_status_choices=tuple(quick_edit_status_choices),
        initial_quick_edit_status=initial_status,
        can_delete=can_delete,
        delete_error_message=delete_error_message,
    )


__all__ = [
    'CANCELED_STATUS',
    'COMPLETED_STATUS',
    'ClassGridSessionPolicy',
    'SCHEDULED_STATUS',
    'build_class_grid_session_policy',
]