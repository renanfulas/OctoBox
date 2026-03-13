"""
ARQUIVO: adapter Django de auditoria da grade de aulas.

POR QUE ELE EXISTE:
- Isola a escrita concreta de auditoria para que o adapter principal da grade nao dependa diretamente de log_audit_event.

O QUE ESTE ARQUIVO FAZ:
1. Reidrata actor e targets ORM da grade.
2. Registra criacao recorrente, edicao e exclusao de aulas.

PONTOS CRITICOS:
- Esta camada pode usar ORM e auditoria concreta livremente, mas nao deve concentrar a persistencia principal da grade.
"""

from django.contrib.auth import get_user_model

from auditing import log_audit_event
from operations.application.commands import (
    ClassScheduleCreateCommand,
    ClassSessionDeleteCommand,
    ClassSessionUpdateCommand,
)
from operations.application.ports import ClassGridAuditPort
from operations.application.results import (
    ClassScheduleCreateResult,
    DeletedClassSessionRecord,
    UpdatedClassSessionRecord,
)
from operations.models import ClassSession


class _DeletedSessionAuditTarget:
    class _Meta:
        model_name = 'classsession'

    _meta = _Meta()

    def __init__(self, result: DeletedClassSessionRecord):
        self.pk = result.id
        self._label = f'{result.title} - {result.scheduled_at:%d/%m %H:%M}'

    def __str__(self):
        return self._label


class DjangoClassGridAudit(ClassGridAuditPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def record_schedule_created(self, *, command: ClassScheduleCreateCommand, result: ClassScheduleCreateResult) -> None:
        actor = self._get_actor(command.actor_id)
        target = None
        if result.created_session_ids:
            target = ClassSession.objects.filter(pk=result.created_session_ids[0]).first()

        log_audit_event(
            actor=actor,
            action='class_schedule_recurring_created',
            target=target,
            description='Agenda recorrente criada pela grade visual de aulas.',
            metadata={
                'title': command.title,
                'coach_id': command.coach_id,
                'start_date': command.start_date.isoformat(),
                'end_date': command.end_date.isoformat(),
                'weekdays': list(command.weekdays),
                'sequence_count': command.sequence_count,
                'created_count': len(result.created_session_ids),
                'skipped_count': len(result.skipped_slots),
            },
        )

    def record_session_updated(self, *, command: ClassSessionUpdateCommand, result: UpdatedClassSessionRecord) -> None:
        actor = self._get_actor(command.actor_id)
        session = ClassSession.objects.get(pk=result.id)
        log_audit_event(
            actor=actor,
            action='class_session_quick_updated',
            target=session,
            description='Aula ajustada pela grade visual.',
            metadata={'status': session.status, 'scheduled_at': session.scheduled_at.isoformat()},
        )

    def record_session_deleted(self, *, command: ClassSessionDeleteCommand, result: DeletedClassSessionRecord) -> None:
        actor = self._get_actor(command.actor_id)
        target = _DeletedSessionAuditTarget(result)
        log_audit_event(
            actor=actor,
            action='class_session_quick_deleted',
            target=target,
            description='Aula excluida pela grade visual.',
            metadata={
                'id': result.id,
                'title': result.title,
                'scheduled_at': result.scheduled_at.isoformat(),
                'status': result.status,
            },
        )


__all__ = ['DjangoClassGridAudit']