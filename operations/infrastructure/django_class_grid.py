"""
ARQUIVO: adapters Django da grade de aulas.

POR QUE ELE EXISTE:
- executa escrita e auditoria concretas da grade fora do catalogo historico.

O QUE ESTE ARQUIVO FAZ:
1. cria agendas recorrentes via ORM.
2. atualiza e exclui aulas com policy e auditoria.
3. mantem a view e as fachadas falando com contracts estaveis.

PONTOS CRITICOS:
- qualquer ajuste aqui impacta mutacoes reais de agenda, entao policy, limites e auditoria precisam continuar juntos.
"""

from django.db import transaction

from operations.application.commands import (
    ClassScheduleCreateCommand,
    ClassSessionDeleteCommand,
    ClassSessionUpdateCommand,
)
from operations.application.ports import ClassGridClockPort, ClassGridWriterPort, UnitOfWorkPort
from operations.application.results import (
    ClassScheduleCreateResult,
    DeletedClassSessionRecord,
    UpdatedClassSessionRecord,
)
from operations.application.use_cases import (
    execute_create_class_schedule_use_case,
    execute_delete_class_session_use_case,
    execute_update_class_session_use_case,
)
from operations.domain import (
    ScheduledClassGridSlot,
    build_class_grid_create_execution_plan,
    build_class_grid_schedule_plan,
    build_class_grid_session_policy,
    collect_changed_field_names,
    should_enforce_schedule_limits_for_status,
)
from operations.infrastructure.django_class_grid_audit import DjangoClassGridAudit
from operations.infrastructure.django_class_grid_clock import DjangoClassGridClockPort
from operations.infrastructure.django_class_grid_coaches import DjangoClassGridCoachResolver
from operations.infrastructure.django_class_grid_sessions import DjangoClassGridSessionStore

from .django_schedule_limits import ensure_schedule_limits


class DjangoAtomicUnitOfWork(UnitOfWorkPort):
    def run(self, operation):
        with transaction.atomic():
            return operation()


class DjangoClassGridWriter(ClassGridWriterPort):
    def __init__(self, *, clock: ClassGridClockPort, coach_resolver: DjangoClassGridCoachResolver, session_store: DjangoClassGridSessionStore):
        self.clock = clock
        self.coach_resolver = coach_resolver
        self.session_store = session_store

    writable_fields = (
        'title',
        'coach',
        'scheduled_at',
        'duration_minutes',
        'capacity',
        'status',
        'notes',
    )

    def create_schedule(self, command: ClassScheduleCreateCommand) -> ClassScheduleCreateResult:
        current_timezone = self.clock.get_current_timezone()
        created_session_ids = []
        coach = self.coach_resolver.resolve(command.coach_id)
        planned_slots = build_class_grid_schedule_plan(
            start_date=command.start_date,
            end_date=command.end_date,
            weekdays=command.weekdays,
            anchor_date=command.anchor_date,
            interval_days=command.interval_days,
            start_time=command.start_time,
            duration_minutes=command.duration_minutes,
            sequence_count=command.sequence_count,
        )
        scheduled_slots = tuple(
            ScheduledClassGridSlot(
                scheduled_date=planned_slot.scheduled_date,
                scheduled_at=self.clock.make_aware(planned_slot.start_at, current_timezone),
            )
            for planned_slot in planned_slots
        )
        existing_scheduled_ats = self.session_store.find_existing_scheduled_ats(
            title=command.title,
            scheduled_ats=[slot.scheduled_at for slot in scheduled_slots],
        )
        execution_plan = build_class_grid_create_execution_plan(
            scheduled_slots=scheduled_slots,
            existing_scheduled_ats=existing_scheduled_ats,
            skip_existing=command.skip_existing,
        )

        for planned_slot in execution_plan.slots_to_create:
            ensure_schedule_limits(
                scheduled_date=planned_slot.scheduled_date,
                pending_day=planned_slot.pending_day,
                pending_week=planned_slot.pending_week,
                pending_month=planned_slot.pending_month,
            )
            session_id = self.session_store.create_session(
                title=command.title,
                coach=coach,
                scheduled_at=planned_slot.scheduled_at,
                duration_minutes=command.duration_minutes,
                capacity=command.capacity,
                status=command.status,
                notes=command.notes,
            )
            created_session_ids.append(session_id)

        return ClassScheduleCreateResult(
            created_session_ids=tuple(created_session_ids),
            skipped_slots=execution_plan.skipped_slots,
        )

    def update_session(self, command: ClassSessionUpdateCommand) -> UpdatedClassSessionRecord:
        session = self.session_store.get_session_for_update(session_id=command.session_id)
        policy = build_class_grid_session_policy(
            initial_status=session.status,
            has_attendance=self.session_store.has_attendance(session=session),
        )
        target_date = command.scheduled_at.date()

        policy.validate_quick_edit_status(command.status)
        if should_enforce_schedule_limits_for_status(command.status):
            ensure_schedule_limits(
                scheduled_date=target_date,
                exclude_session_ids=[session.id],
            )

        target_values = {
            'title': command.title,
            'coach': self.coach_resolver.resolve(command.coach_id),
            'scheduled_at': command.scheduled_at,
            'duration_minutes': command.duration_minutes,
            'capacity': command.capacity,
            'status': command.status,
            'notes': command.notes,
        }
        current_values = self.session_store.collect_current_values(
            session=session,
            field_names=tuple(target_values.keys()),
        )
        changed_fields = collect_changed_field_names(
            current_values=current_values,
            target_values=target_values,
        )
        self.session_store.save_session_updates(
            session=session,
            target_values=target_values,
            changed_fields=changed_fields,
        )

        return UpdatedClassSessionRecord(id=session.id, title=session.title)

    def delete_session(self, command: ClassSessionDeleteCommand) -> DeletedClassSessionRecord:
        session = self.session_store.get_session_for_update(session_id=command.session_id)
        policy = build_class_grid_session_policy(
            initial_status=session.status,
            has_attendance=self.session_store.has_attendance(session=session),
        )
        policy.ensure_can_delete()

        snapshot = DeletedClassSessionRecord(
            id=session.id,
            title=session.title,
            scheduled_at=session.scheduled_at,
            status=session.status,
        )
        self.session_store.delete_session(session=session)
        return snapshot


def _build_dependencies():
    return {
        'unit_of_work': DjangoAtomicUnitOfWork(),
        'writer': DjangoClassGridWriter(
            clock=DjangoClassGridClockPort(),
            coach_resolver=DjangoClassGridCoachResolver(),
            session_store=DjangoClassGridSessionStore(),
        ),
        'audit': DjangoClassGridAudit(),
    }


def execute_create_class_schedule_command(command: ClassScheduleCreateCommand):
    return execute_create_class_schedule_use_case(command, **_build_dependencies())


def execute_update_class_session_command(command: ClassSessionUpdateCommand):
    return execute_update_class_session_use_case(command, **_build_dependencies())


def execute_delete_class_session_command(command: ClassSessionDeleteCommand):
    return execute_delete_class_session_use_case(command, **_build_dependencies())


__all__ = [
    'execute_create_class_schedule_command',
    'execute_delete_class_session_command',
    'execute_update_class_session_command',
]
