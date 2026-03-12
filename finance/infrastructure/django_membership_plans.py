"""
ARQUIVO: adapters Django dos workflows leves de plano.

POR QUE ELE EXISTE:
- Implementa a escrita e auditoria concreta de plano fora da casca historica do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. Persiste criacao e edicao de MembershipPlan via ORM.
2. Registra auditoria comercial do portfolio.
3. Mantem a camada historica como fachada fina.

PONTOS CRITICOS:
- Esta camada pode usar Django livremente, mas o contrato para cima deve continuar estavel.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from boxcore.auditing import log_audit_event
from boxcore.models import MembershipPlan
from finance.application.commands import MembershipPlanCommand
from finance.application.ports import MembershipPlanAuditPort, MembershipPlanWriterPort, UnitOfWorkPort
from finance.application.results import MembershipPlanRecord
from finance.application.use_cases import (
    execute_create_membership_plan_use_case,
    execute_update_membership_plan_use_case,
)


class DjangoAtomicUnitOfWork(UnitOfWorkPort):
    def run(self, operation):
        with transaction.atomic():
            return operation()


class DjangoMembershipPlanWriter(MembershipPlanWriterPort):
    writable_fields = (
        'name',
        'price',
        'billing_cycle',
        'sessions_per_week',
        'description',
        'active',
    )

    def _build_values(self, command: MembershipPlanCommand):
        return {field_name: getattr(command, field_name) for field_name in self.writable_fields}

    def create(self, command: MembershipPlanCommand) -> MembershipPlanRecord:
        plan = MembershipPlan.objects.create(**self._build_values(command))
        return MembershipPlanRecord(id=plan.id, name=plan.name)

    def update(self, command: MembershipPlanCommand) -> MembershipPlanRecord:
        if command.plan_id is None:
            raise ValueError('plan_id is required to update a membership plan.')

        plan = MembershipPlan.objects.select_for_update().get(pk=command.plan_id)
        update_fields = []
        for field_name, value in self._build_values(command).items():
            if getattr(plan, field_name) != value:
                setattr(plan, field_name, value)
                update_fields.append(field_name)

        if update_fields:
            update_fields.append('updated_at')
            plan.save(update_fields=update_fields)

        return MembershipPlanRecord(id=plan.id, name=plan.name)


class DjangoMembershipPlanAudit(MembershipPlanAuditPort):
    def __init__(self):
        self.user_model = get_user_model()

    def _get_actor(self, actor_id: int | None):
        if actor_id is None:
            return None
        return self.user_model.objects.filter(pk=actor_id).first()

    def _get_plan(self, plan_id: int):
        return MembershipPlan.objects.get(pk=plan_id)

    def record_created(self, *, command: MembershipPlanCommand, result: MembershipPlanRecord) -> None:
        actor = self._get_actor(command.actor_id)
        plan = self._get_plan(result.id)
        log_audit_event(
            actor=actor,
            action='membership_plan_quick_created',
            target=plan,
            description='Plano criado pela central visual de financeiro.',
            metadata={'price': str(plan.price), 'billing_cycle': plan.billing_cycle},
        )

    def record_updated(self, *, command: MembershipPlanCommand, result: MembershipPlanRecord) -> None:
        actor = self._get_actor(command.actor_id)
        plan = self._get_plan(result.id)
        log_audit_event(
            actor=actor,
            action='membership_plan_quick_updated',
            target=plan,
            description='Plano alterado pela central visual de financeiro.',
            metadata={'changed_fields': list(command.changed_fields)},
        )


def _build_dependencies():
    return {
        'unit_of_work': DjangoAtomicUnitOfWork(),
        'writer': DjangoMembershipPlanWriter(),
        'audit': DjangoMembershipPlanAudit(),
    }


def execute_create_membership_plan_command(command: MembershipPlanCommand):
    return execute_create_membership_plan_use_case(command, **_build_dependencies())


def execute_update_membership_plan_command(command: MembershipPlanCommand):
    return execute_update_membership_plan_use_case(command, **_build_dependencies())


__all__ = ['execute_create_membership_plan_command', 'execute_update_membership_plan_command']